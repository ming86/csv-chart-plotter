"""
Logging Configuration - Consistent logging setup for the application.
"""

import logging
import sys


def configure_logging(level: int = logging.INFO) -> None:
    """
    Configure root logger with consistent format.

    Args:
        level: Logging level (default: INFO)
    """
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[logging.StreamHandler(sys.stderr)]
    )
