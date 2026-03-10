"""Logging setup helpers."""

from __future__ import annotations

import logging
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

LOG_FILENAME = "sm-tracker.log"
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%dT%H:%M:%S"


def setup_logging(
    logs_path: Path,
    level: str = "INFO",
    retention_days: int = 14,
    logger_name: str = "sm_tracker",
) -> logging.Logger:
    """Configure and return a named logger with console and rotating file handlers."""
    logs_path.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger(logger_name)
    _reset_handlers(logger)

    logger.propagate = False
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))

    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)
    file_handler = TimedRotatingFileHandler(
        filename=logs_path / LOG_FILENAME,
        when="midnight",
        interval=1,
        backupCount=retention_days,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(logger.level)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logger.level)

    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    return logger


def _reset_handlers(logger: logging.Logger) -> None:
    """Detach and close any existing handlers before reconfiguring the logger."""
    for handler in list(logger.handlers):
        logger.removeHandler(handler)
        handler.close()
