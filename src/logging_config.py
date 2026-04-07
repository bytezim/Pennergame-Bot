import logging
import sys
from pathlib import Path
from typing import Optional


def setup_logging(
    level: int = logging.INFO,
    log_file: Optional[str] = None,
    format_string: Optional[str] = None,
) -> logging.Logger:
    if format_string is None:
        format_string = "%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s"
    formatter = logging.Formatter(format_string)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    console_handler.encoding = "utf-8"
    root_logger = logging.getLogger()
    root_logger.setLevel(level)
    has_stdout_handler = False
    for h in root_logger.handlers:
        try:
            if (
                isinstance(h, logging.StreamHandler)
                and getattr(h, "stream", None) is sys.stdout
            ):
                has_stdout_handler = True
                break
        except Exception:
            continue
    if not has_stdout_handler:
        root_logger.addHandler(console_handler)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        file_path_str = str(log_path)
        has_same_file_handler = any(
            (
                isinstance(h, logging.FileHandler)
                and getattr(h, "baseFilename", None) == file_path_str
                for h in root_logger.handlers
            )
        )
        if not has_same_file_handler:
            root_logger.addHandler(file_handler)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    for name in logging.Logger.manager.loggerDict:
        if name.startswith("apscheduler"):
            logging.getLogger(name).setLevel(logging.WARNING)
    return root_logger


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)


BOT_LEVEL = 25
logging.addLevelName(BOT_LEVEL, "BOT")


def bot_log(self, message, *args, **kwargs):
    if self.isEnabledFor(BOT_LEVEL):
        self._log(BOT_LEVEL, message, args, **kwargs)


logging.Logger.bot = bot_log
