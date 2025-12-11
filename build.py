"""
Nuitka build script for CSV Chart Plotter standalone executable.

Compiles Python application to native Windows executable with all dependencies
bundled. No Python installation required on target system.

Usage:
    python build.py

Output:
    dist/csv-chart-plotter.exe (standalone executable)

Requirements:
    - Nuitka installed: uv add --optional nuitka
    - C compiler available (MSVC, MinGW, or Clang)
    - Windows OS (for .exe generation)
"""

import logging
import shutil
import subprocess
import sys
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def check_nuitka() -> bool:
    """Verify Nuitka is available in environment."""
    try:
        # Try direct Python module access first
        result = subprocess.run(
            [sys.executable, '-m', 'nuitka', '--version'],
            capture_output=True,
            text=True,
            check=False  # Don't raise on non-zero exit (version check may have warnings)
        )
        # Check if version info present in output
        if '2.' in result.stdout or 'Nuitka' in result.stdout:
            # Extract version line only
            version_line = result.stdout.split('\n')[0]
            logger.info(f"Nuitka version: {version_line}")
            return True
        raise FileNotFoundError("Nuitka not found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        logger.error("Nuitka not found. Install with: uv add --optional build nuitka")
        return False


def check_compiler() -> bool:
    """Verify C compiler is available for Nuitka compilation."""
    if sys.platform == 'win32':
        # Check for MSVC (cl.exe)
        try:
            result = subprocess.run(
                ['cl.exe'],
                capture_output=True,
                text=True,
                check=False
            )
            if 'Microsoft' in result.stderr:
                logger.info("MSVC compiler detected")
                return True
        except FileNotFoundError:
            pass
        
        logger.error("MSVC compiler not found.")
        logger.error("")
        logger.error("Install Visual Studio Build Tools:")
        logger.error("  1. Download from: https://visualstudio.microsoft.com/downloads/")
        logger.error("  2. Select 'Build Tools for Visual Studio 2022'")
        logger.error("  3. Check 'Desktop development with C++'")
        logger.error("")
        logger.error("Then run build from 'Developer Command Prompt for VS 2022'")
        return False
    
    elif sys.platform == 'darwin':
        # Check for Clang (macOS)
        try:
            result = subprocess.run(
                ['clang', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'clang' in result.stdout.lower():
                logger.info("Clang compiler detected")
                return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.error("Clang not found. Install: xcode-select --install")
            return False
    
    else:
        # Check for GCC (Linux)
        try:
            result = subprocess.run(
                ['gcc', '--version'],
                capture_output=True,
                text=True,
                check=True
            )
            if 'gcc' in result.stdout.lower():
                logger.info("GCC compiler detected")
                return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            logger.error("GCC not found. Install: sudo apt install build-essential")
            return False
    
    return False


def clean_dist() -> None:
    """Remove previous build artifacts."""
    dist_dir = Path('dist')
    if dist_dir.exists():
        logger.info("Cleaning previous build artifacts...")
        shutil.rmtree(dist_dir)


def build_executable() -> int:
    """
    Compile application using Nuitka.

    Returns:
        Exit code (0 = success, non-zero = failure)
    """
    logger.info("Starting Nuitka compilation...")
    
    # Nuitka command with required flags
    cmd = [
        sys.executable, '-m', 'nuitka',
        '--standalone',  # Bundle all dependencies
        '--onefile',  # Single executable file
        '--enable-plugin=no-qt',  # Disable Qt plugin auto-detection
        '--follow-imports',  # Include all imported modules
        '--include-package=pandas',  # Required: pandas data structures
        '--include-package=plotly',  # Required: chart rendering
        '--include-package=dash',  # Required: web framework
        '--include-package=flask',  # Required: Dash dependency
        '--include-package=werkzeug',  # Required: Flask dependency
        '--include-package-data=plotly',  # Include plotly data files
        '--include-package-data=dash',  # Include dash data files
        '--nofollow-import-to=pytest',  # Exclude test framework
        '--nofollow-import-to=unittest',  # Exclude test framework
        '--nofollow-import-to=test',  # Exclude test modules
        '--windows-console-mode=disable',  # No console window on Windows
        '--output-dir=dist',  # Output directory
        '--output-filename=csv-chart-plotter.exe',  # Executable name
        'src/csv_chart_plotter/main.py',  # Entry point
    ]
    
    logger.info("Nuitka command:")
    logger.info(" ".join(cmd))
    
    try:
        result = subprocess.run(
            cmd,
            check=True,
            text=True,
            # Stream output to console
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        return result.returncode
    except subprocess.CalledProcessError as e:
        logger.error(f"Compilation failed with exit code {e.returncode}")
        return e.returncode


def verify_executable() -> bool:
    """Check that executable was created successfully."""
    exe_path = Path('dist/csv-chart-plotter.exe')
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        logger.info(f"Executable created: {exe_path}")
        logger.info(f"Size: {size_mb:.2f} MB")
        return True
    else:
        logger.error("Executable not found in dist/")
        return False


def main() -> int:
    """
    Execute build pipeline.

    Returns:
        Exit code (0 = success, 1 = failure)
    """
    logger.info("=== CSV Chart Plotter Build Script ===")
    
    # Pre-flight checks
    if not check_nuitka():
        return 1
    
    if not check_compiler():
        return 1
    
    # Clean previous builds
    clean_dist()
    
    # Compile with Nuitka
    result = build_executable()
    if result != 0:
        logger.error("Build failed")
        return 1
    
    # Verify output
    if not verify_executable():
        return 1
    
    logger.info("=== Build completed successfully ===")
    logger.info("Run: dist\\csv-chart-plotter.exe sample.csv")
    return 0


if __name__ == '__main__':
    sys.exit(main())
