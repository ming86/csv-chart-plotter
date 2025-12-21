"""
CSV Chart Plotter - Main entry point.

Interactive CSV time-series visualizer using Dash + pywebview.
"""

import argparse
import logging
import socket
import sys
import threading
from pathlib import Path
from typing import Any, Optional, TYPE_CHECKING

from .logging_config import configure_logging

# Defer heavy imports (pandas, numpy, plotly, webview) until after CLI parsing
if TYPE_CHECKING:
    import webview
    from .csv_indexer import CSVIndexer

logger = logging.getLogger(__name__)

WINDOW_WIDTH = 1200
WINDOW_HEIGHT = 800
DEFAULT_THEME = "light"

# Global reference for pywebview API
_app_state: dict[str, Any] = {
    "window": None,
    "app": None,
    "selected_file": None,
}


class PyWebViewAPI:
    """JavaScript API exposed to pywebview for file dialog access."""

    def open_file_dialog(self) -> Optional[str]:
        """
        Open a native file dialog and return the selected file path.

        Returns:
            Selected file path, or None if cancelled.
        """
        window = _app_state.get("window")
        if window is None:
            logger.warning("No window available for file dialog")
            return None

        try:
            result = window.create_file_dialog(
                webview.OPEN_DIALOG,
                file_types=("CSV files (*.csv)",),
            )
            if result and len(result) > 0:
                selected = result[0]
                logger.info("File selected via dialog: %s", selected)
                _app_state["selected_file"] = selected
                return selected
            return None
        except Exception as e:
            logger.error("File dialog error: %s", e)
            return None

    def get_selected_file(self) -> Optional[str]:
        """Get the most recently selected file path."""
        return _app_state.get("selected_file")


def find_available_port(start: int = 8050, max_attempts: int = 100) -> int:
    """
    Find an available port starting from the given port.

    Iterates through ports beginning at `start`, testing each for availability
    by attempting to bind a socket. Returns the first port that can be bound.

    Args:
        start: Port to start searching from.
        max_attempts: Maximum number of ports to try.

    Returns:
        Available port number.

    Raises:
        RuntimeError: If no available port found within max_attempts.
    """
    for offset in range(max_attempts):
        port = start + offset
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.bind(("127.0.0.1", port))
                logger.debug("Found available port: %d", port)
                return port
        except OSError:
            continue
    raise RuntimeError(
        f"No available port found in range {start}-{start + max_attempts - 1}"
    )


def validate_file(file_path: Path) -> None:
    """
    Validate that the CSV file exists and is accessible.

    Args:
        file_path: Path to validate.

    Raises:
        FileNotFoundError: If file does not exist.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"CSV file not found: {file_path}")
    if not file_path.is_file():
        raise FileNotFoundError(f"Path is not a file: {file_path}")


def run_server(app: Any, port: int) -> None:
    """
    Run the Flask server in the current thread.

    This function is intended to be executed in a background daemon thread.
    The server runs with threading enabled and debug mode disabled for
    production stability.

    Args:
        app: Dash application instance.
        port: Port to listen on.
    """
    logger.info("Starting Flask server on port %d", port)
    app.run(
        host="127.0.0.1",
        port=port,
        debug=False,
        threaded=True,
        use_reloader=False,
    )


def main() -> int:
    """
    Main entry point for CSV Chart Plotter.

    Parses CLI arguments, validates input file (if provided), initializes the
    Dash application, starts the Flask server in a background thread, and
    creates a pywebview window that blocks until closed.

    Returns:
        Exit code:
        - 0: Success (window closed normally)
        - 1: Data error (file not found, no numeric columns)
        - 2: Unexpected error
    """
    configure_logging()

    parser = argparse.ArgumentParser(
        prog="csv_chart_plotter",
        description="Interactive CSV time-series chart viewer",
    )
    parser.add_argument(
        "csv_file",
        nargs="?",
        default=None,
        help="(Optional) Path to CSV file to visualize",
    )
    parser.add_argument(
        "--follow",
        action="store_true",
        help="Enable follow mode (auto-reload on file changes)",
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark"],
        default=DEFAULT_THEME,
        help="Initial color theme (default: light); switchable via UI",
    )

    args = parser.parse_args()

    try:
        # Defer heavy imports until after CLI parsing to reduce perceived startup time
        import webview
        from .chart_app import create_app
        from .csv_indexer import CSVIndexer
        from .column_filter import filter_numeric_columns

        csv_path: Optional[Path] = None
        window_title = "CSV Chart Plotter"
        indexer: Optional[CSVIndexer] = None

        if args.csv_file:
            csv_path = Path(args.csv_file).resolve()
            validate_file(csv_path)

            logger.info("Loading CSV: %s", csv_path)

            # Build index and load data
            indexer = CSVIndexer(csv_path)
            index = indexer.build_index()

            logger.info(
                "Indexed %d rows, %d columns from %s",
                index.row_count,
                len(index.columns),
                csv_path.name,
            )

            # Read all data for initial display (LTTB downsampling handles large files)
            df = indexer.read_range(0, index.row_count)

            # Filter to numeric columns only
            df_numeric = filter_numeric_columns(df)

            logger.info(
                "Filtered to %d numeric columns: %s",
                len(df_numeric.columns),
                list(df_numeric.columns),
            )

            window_title = f"CSV Chart Plotter - {csv_path.name}"

            # Create Dash app with data
            app = create_app(
                df=df_numeric,
                csv_filename=csv_path.name,
                csv_filepath=str(csv_path) if args.follow else None,
                theme=args.theme,
                follow_mode=args.follow,
                indexer=indexer,
            )
        else:
            # No file provided - create app in empty state
            logger.info("No CSV file provided; starting in empty state")
            app = create_app(
                df=None,
                csv_filename=None,
                csv_filepath=None,
                theme=args.theme,
                follow_mode=False,
                indexer=None,
            )

        # Find available port
        port = find_available_port()
        logger.info("Using port %d for Flask server", port)

        # Start Flask server in background daemon thread
        server_thread = threading.Thread(
            target=run_server,
            args=(app, port),
            daemon=True,
            name="FlaskServer",
        )
        server_thread.start()

        # Create pywebview window (blocks until closed)
        url = f"http://127.0.0.1:{port}/"
        logger.info("Creating pywebview window: %s", url)

        # Create API instance for JavaScript bridge
        api = PyWebViewAPI()

        window = webview.create_window(
            title=window_title,
            url=url,
            width=WINDOW_WIDTH,
            height=WINDOW_HEIGHT,
            js_api=api,
        )

        # Store references for API access
        _app_state["window"] = window
        _app_state["app"] = app
        app._pywebview_window = window

        # Block on main thread until window closes
        webview.start()

        logger.info("Window closed; exiting")
        return 0

    except FileNotFoundError as e:
        logger.error("File error: %s", e)
        return 1

    except ValueError as e:
        # Raised by filter_numeric_columns when no numeric columns remain
        logger.error("Data error: %s", e)
        return 1

    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        return 2


if __name__ == "__main__":
    sys.exit(main())
