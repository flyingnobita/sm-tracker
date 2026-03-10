"""Phase 2 logging tests."""

import importlib
import io
from logging import StreamHandler
from logging.handlers import TimedRotatingFileHandler
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
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


def test_setup_logging_replaces_stale_console_stream_handler(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    logger_name = "sm_tracker_stale_stream_test"
    logger = setup_logging(
        logs_path=tmp_path / "logs",
        level="INFO",
        retention_days=7,
        logger_name=logger_name,
    )

    stale_stream = io.StringIO()
    stale_console = next(
        h
        for h in logger.handlers
        if isinstance(h, StreamHandler) and not isinstance(h, TimedRotatingFileHandler)
    )
    stale_console.setStream(stale_stream)
    stale_stream.close()

    reconfigured = setup_logging(
        logs_path=tmp_path / "logs",
        level="INFO",
        retention_days=7,
        logger_name=logger_name,
    )
    reconfigured.info("fresh console handler works")
    for handler in reconfigured.handlers:
        handler.flush()

    captured = capsys.readouterr()
    assert "fresh console handler works" in captured.err


def test_cli_bootstrap_creates_configured_log_file(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sm_tracker.cli.track.resolve_adapters",
        lambda _platforms, env=None: (
            [],
            ["Skipping twitter: missing TWITTER_CONSUMER_KEY in environment."],
        ),
    )
    runner = CliRunner()
    import logging

    logging.getLogger("sm_tracker").handlers.clear()
    with runner.isolated_filesystem():
        Path("config.toml").write_text(
            (
                'profile = "dev"\n'
                "\n"
                "[paths.dev]\n"
                'db = "./data-dev.db"\n'
                'logs = "./logs-dev"\n'
                "\n"
                "[logging.dev]\n"
                "retention_days = 7\n"
                'level = "INFO"\n'
            ),
            encoding="utf-8",
        )
        result = runner.invoke(app, ["track", "-p", "twitter"])
        log_path = Path("logs-dev", LOG_FILENAME)
        assert log_path.exists()
        contents = log_path.read_text(encoding="utf-8")
        assert "CLI logging initialized" in contents
        assert "track command started" in contents
        assert "track command finished with no adapters" in contents

    assert result.exit_code == 0


def test_cli_help_survives_unwritable_configured_log_path(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    import logging

    cli_app_module = importlib.import_module("sm_tracker.cli.app")
    logging.getLogger("sm_tracker").handlers.clear()
    monkeypatch.setattr(
        cli_app_module,
        "setup_logging",
        lambda **_kwargs: (_ for _ in ()).throw(OSError("permission denied")),
    )
    with runner.isolated_filesystem():
        Path("config.toml").write_text(
            (
                'profile = "dev"\n'
                "\n"
                "[paths.dev]\n"
                'db = "./data-dev.db"\n'
                'logs = "./logs-dev"\n'
                "\n"
                "[logging.dev]\n"
                "retention_days = 7\n"
                'level = "INFO"\n'
            ),
            encoding="utf-8",
        )

        result = runner.invoke(app, ["help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
