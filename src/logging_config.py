"""
Centralized logging configuration.

Provides structured logging with proper levels and formatting.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

# ===========================
# Logging Configuration
# ===========================


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    """
    Configure application-wide logging.

    Args:
        level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Optional file path for file logging
        format_string: Custom log format string

    Returns:
        Configured logger instance
    """
    if format_string is None:
        format_string = (
            "%(asctime)s - %(name)s - %(levelname)s - "
            "%(funcName)s:%(lineno)d - %(message)s"
        )

    # Create formatter
    formatter = logging.Formatter(format_string)

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.encoding = "utf-8"  # Ensure proper Unicode handling for emojis

    # Root logger configuration
    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Avoid adding duplicate console handlers when setup is called multiple times
    has_stdout_handler = False
    for h in root_logger.handlers:
        try:
            if isinstance(h, logging.StreamHandler) and getattr(h, "stream", None) is sys.stdout:
                has_stdout_handler = True
                break
        except Exception:
            continue

    if not has_stdout_handler:
        root_logger.addHandler(console_handler)

    # Optional file handler
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)

        # Avoid adding the same file handler multiple times
        file_path_str = str(log_path)
        has_same_file_handler = any(
            isinstance(h, logging.FileHandler) and getattr(h, "baseFilename", None) == file_path_str
            for h in root_logger.handlers
        )
        if not has_same_file_handler:
            root_logger.addHandler(file_handler)

    # Suppress noisy libraries
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("apscheduler").setLevel(logging.WARNING)

    return root_logger


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for a module.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)


# ===========================
# Custom Log Levels
# ===========================

# Add custom BOT level between INFO and WARNING
BOT_LEVEL = 25
logging.addLevelName(BOT_LEVEL, "BOT")


def bot_log(self, message, *args, **kwargs):
    """Log with custom BOT level."""
    if self.isEnabledFor(BOT_LEVEL):
        self._log(BOT_LEVEL, message, args, **kwargs)


# Add to Logger class
logging.Logger.bot = bot_log  # type: ignore
