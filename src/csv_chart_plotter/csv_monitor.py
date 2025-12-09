"""
CSV Monitor - Watchdog-based file change detection.

Provides debounced file modification events for follow mode.
Implements FR-FOLLOW-01 through FR-FOLLOW-09 from specification.
"""

import time
import logging
from pathlib import Path
from typing import Callable, Optional
from threading import Lock

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileDeletedEvent

logger = logging.getLogger(__name__)

DEBOUNCE_INTERVAL = 5.0  # seconds


class CSVFileHandler(FileSystemEventHandler):
    """
    Handles file modification events with debouncing.
    
    Debounce timing measures from render completion, not event trigger.
    This prevents update storms when the chart is still rendering.
    """
    
    def __init__(
        self,
        file_path: Path,
        on_change: Callable[[Path, bool], None]
    ):
        """
        Initialize the file handler.
        
        Args:
            file_path: Path to monitored CSV file.
            on_change: Callback invoked when file changes (debounced).
                       Receives (file_path, is_truncation) parameters.
        """
        super().__init__()
        self.file_path = file_path.resolve()
        self.on_change = on_change
        self.last_complete_time = 0.0
        self._lock = Lock()
        self._last_size = self._get_file_size()
        self._file_deleted = False
    
    def _get_file_size(self) -> int:
        """Get current file size, returning 0 if file does not exist."""
        try:
            return self.file_path.stat().st_size
        except (FileNotFoundError, OSError):
            return 0
    
    def on_modified(self, event: FileModifiedEvent) -> None:
        """
        Handle file modification events.
        
        Applies debouncing based on last render completion time.
        Detects file truncation via size comparison.
        """
        if event.is_directory:
            return
        
        event_path = Path(event.src_path).resolve()
        if event_path != self.file_path:
            return
        
        with self._lock:
            # Clear deleted flag if file reappears
            if self._file_deleted:
                logger.info("Monitored file reappeared: %s", self.file_path)
                self._file_deleted = False
            
            current_time = time.time()
            
            # Debounce: skip if insufficient time since last render completion
            if current_time - self.last_complete_time < DEBOUNCE_INTERVAL:
                logger.debug(
                    "Debouncing file change - %.1fs since last render complete",
                    current_time - self.last_complete_time
                )
                return
            
            # Detect file size change
            current_size = self._get_file_size()
            previous_size = self._last_size
            
            if current_size == previous_size:
                # File modified but size unchanged - likely metadata or same-length content
                logger.debug("File modified but size unchanged, skipping update")
                return
            
            is_truncation = current_size < previous_size
            
            if is_truncation:
                logger.warning(
                    "File truncation detected: %d -> %d bytes. Triggering full reload.",
                    previous_size,
                    current_size
                )
            else:
                logger.debug(
                    "File growth detected: %d -> %d bytes",
                    previous_size,
                    current_size
                )
            
            self._last_size = current_size
        
        # Invoke callback outside lock to prevent deadlocks
        try:
            self.on_change(self.file_path, is_truncation)
        except Exception:
            logger.exception("Error in file change callback")
    
    def on_deleted(self, event: FileDeletedEvent) -> None:
        """
        Handle file deletion events.
        
        Logs warning but continues polling - file may reappear.
        """
        if event.is_directory:
            return
        
        event_path = Path(event.src_path).resolve()
        if event_path != self.file_path:
            return
        
        with self._lock:
            if not self._file_deleted:
                logger.warning(
                    "Monitored file deleted: %s. Continuing to poll.",
                    self.file_path
                )
                self._file_deleted = True
                self._last_size = 0
    
    def mark_render_complete(self) -> None:
        """
        Mark that a render operation has completed.
        
        Resets the debounce timer, allowing the next file change
        to trigger an update after DEBOUNCE_INTERVAL elapses.
        """
        with self._lock:
            self.last_complete_time = time.time()
            logger.debug("Render complete marked at %.3f", self.last_complete_time)
    
    def reset_file_size(self) -> None:
        """
        Reset tracked file size to current actual size.
        
        Call after a full index rebuild to resynchronize state.
        """
        with self._lock:
            self._last_size = self._get_file_size()
            logger.debug("File size reset to %d bytes", self._last_size)


class CSVMonitor:
    """
    Monitors a CSV file for changes using watchdog.
    
    Provides debounced file modification detection suitable for
    follow mode, where the chart updates as new data arrives.
    
    Usage:
        def handle_change(path: Path, is_truncation: bool) -> None:
            if is_truncation:
                rebuild_index()
            else:
                append_new_rows()
        
        monitor = CSVMonitor(Path("data.csv"), on_change=handle_change)
        monitor.start()
        
        # After each chart render completes:
        monitor.mark_render_complete()
        
        # When done:
        monitor.stop()
    """
    
    def __init__(
        self,
        file_path: Path,
        on_change: Callable[[Path, bool], None]
    ):
        """
        Initialize the CSV monitor.
        
        Args:
            file_path: Path to CSV file to monitor.
            on_change: Callback for file changes. Receives two arguments:
                       - file_path: Path to the changed file
                       - is_truncation: True if file was truncated (size decreased)
        """
        self.file_path = Path(file_path).resolve()
        self.on_change = on_change
        self._observer: Optional[Observer] = None
        self._handler: Optional[CSVFileHandler] = None
        self._lock = Lock()
    
    def start(self) -> None:
        """
        Start monitoring the file.
        
        Creates a watchdog observer that monitors the parent directory
        and filters events for the target file.
        
        Raises:
            RuntimeError: If monitor is already running.
            FileNotFoundError: If the file's parent directory does not exist.
        """
        with self._lock:
            if self._observer is not None:
                raise RuntimeError("Monitor is already running")
            
            parent_dir = self.file_path.parent
            if not parent_dir.exists():
                raise FileNotFoundError(
                    f"Parent directory does not exist: {parent_dir}"
                )
            
            self._handler = CSVFileHandler(self.file_path, self.on_change)
            self._observer = Observer()
            self._observer.schedule(
                self._handler,
                str(parent_dir),
                recursive=False
            )
            self._observer.start()
            
            logger.info("Started monitoring: %s", self.file_path)
    
    def stop(self) -> None:
        """
        Stop monitoring and clean up resources.
        
        Safe to call multiple times or if never started.
        """
        with self._lock:
            if self._observer is not None:
                self._observer.stop()
                self._observer.join(timeout=5.0)
                
                if self._observer.is_alive():
                    logger.warning("Observer thread did not terminate cleanly")
                
                self._observer = None
                self._handler = None
                
                logger.info("Stopped monitoring: %s", self.file_path)
    
    def mark_render_complete(self) -> None:
        """
        Mark that a render operation has completed.
        
        Call this after chart updates to reset the debounce timer.
        The next file change will only trigger an update after
        DEBOUNCE_INTERVAL seconds have elapsed.
        """
        with self._lock:
            if self._handler is not None:
                self._handler.mark_render_complete()
    
    def reset_file_tracking(self) -> None:
        """
        Reset file size tracking to current state.
        
        Call after a full index rebuild (e.g., after truncation)
        to resynchronize the monitor's internal state.
        """
        with self._lock:
            if self._handler is not None:
                self._handler.reset_file_size()
    
    def trigger_manual_reload(self) -> None:
        """
        Trigger an immediate reload, bypassing debounce.
        
        Used for the manual reload button (FR-FOLLOW-09).
        Forces a full reload regardless of debounce state.
        """
        logger.info("Manual reload triggered for: %s", self.file_path)
        try:
            self.on_change(self.file_path, True)  # Treat as truncation for full reload
        except Exception:
            logger.exception("Error during manual reload")
    
    @property
    def is_running(self) -> bool:
        """Whether the monitor is currently active."""
        with self._lock:
            return self._observer is not None and self._observer.is_alive()
    
    def __enter__(self) -> "CSVMonitor":
        """Context manager entry - starts monitoring."""
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Context manager exit - stops monitoring."""
        self.stop()
