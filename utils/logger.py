"""
Structured logging for the AI Job Hunter Agent.

Provides agent-specific loggers with consistent formatting,
console + file output, and color-coded levels.
"""

import logging
import sys
from pathlib import Path


_LOG_FORMAT = "%(asctime)s │ %(levelname)-8s │ %(name)-20s │ %(message)s"
_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

_initialized = False


def setup_logging(level: str = "INFO", log_dir: str | None = None) -> None:
    """
    Initialize the root logger with console and optional file handlers.

    Call once at application startup (main.py).

    Args:
        level: Log level string (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_dir: Optional directory path for log file output.
    """
    global _initialized
    if _initialized:
        return

    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    # ─── Console Handler ───
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
    root_logger.addHandler(console_handler)

    # ─── File Handler (optional) ───
    if log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_path / "job_agent.log", encoding="utf-8")
        file_handler.setFormatter(logging.Formatter(_LOG_FORMAT, datefmt=_DATE_FORMAT))
        root_logger.addHandler(file_handler)

    # Quiet noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("gspread").setLevel(logging.WARNING)
    logging.getLogger("google").setLevel(logging.WARNING)

    _initialized = True


def get_logger(name: str) -> logging.Logger:
    """
    Get a named logger for a specific module or agent.

    Usage:
        from utils.logger import get_logger
        logger = get_logger("scraper.greenhouse")
        logger.info("Found 15 new jobs")

    Args:
        name: Logger name, typically module or agent name.

    Returns:
        Configured Logger instance.
    """
    return logging.getLogger(name)
