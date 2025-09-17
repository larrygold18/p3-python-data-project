"""
utils_logger.py
Provides a get_logger() function so project3.py can import and use it.
"""

import os
import sys
from loguru import logger as _logger

def get_logger(name: str = "app", log_file: str = "logs/app.log"):
    """
    Configure and return a loguru logger instance.

    Args:
        name (str): Not used heavily here, but included for compatibility.
        log_file (str): Path to the log file to write logs to.

    Returns:
        logger: Configured loguru logger.
    """
    # make sure the log folder exists
    folder = os.path.dirname(log_file) or "."
    os.makedirs(folder, exist_ok=True)

    # reset any existing handlers
    _logger.remove()

    # log to console
    _logger.add(sys.stderr, level="INFO")

    # log to file
    _logger.add(
        log_file,
        level="INFO",
        encoding="utf-8",
        rotation="1 MB",
        retention=5,
        enqueue=True
    )

    _logger.info(f"Logger initialized. Writing to {log_file}")
    return _logger
