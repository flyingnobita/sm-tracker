"""Phase 2 logging tests."""

from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import pytest

from sm_tracker.logging import LOG_FILENAME, setup_logging


def test_setup_logging_writes_to_file_and_console(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    logger = setup_logging(
        logs_path=tmp_path / "logs",
        level="INFO",
        retention_days=7,
        logger_name="sm_tracker_test",
    )

    logger.info("phase2 logging works")
    for handler in logger.handlers:
        handler.flush()

    file_output = (tmp_path / "logs" / LOG_FILENAME).read_text(encoding="utf-8")
    assert "phase2 logging works" in file_output

    captured = capsys.readouterr()
    assert "phase2 logging works" in captured.err


def test_setup_logging_uses_timed_rotation_settings(tmp_path: Path) -> None:
    logger = setup_logging(
        logs_path=tmp_path / "logs",
        level="DEBUG",
        retention_days=5,
        logger_name="sm_tracker_rotation_test",
    )

    file_handlers = [h for h in logger.handlers if isinstance(h, TimedRotatingFileHandler)]
    assert len(file_handlers) == 1
    file_handler = file_handlers[0]

    assert file_handler.when == "MIDNIGHT"
    assert file_handler.backupCount == 5
    assert file_handler.interval == 60 * 60 * 24

    console_handlers = [
        h
        for h in logger.handlers
        if isinstance(h, StreamHandler) and not isinstance(h, TimedRotatingFileHandler)
    ]
    assert len(console_handlers) == 1
