"""Phase 2 config loading tests."""

import os
from pathlib import Path

import pytest

from sm_tracker.config import ConfigError, load_config, load_env_file, read_env_file, resolve_profile


def test_load_env_file_reads_dotenv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("SM_TRACKER_TEST_ENV=hello\n", encoding="utf-8")
    monkeypatch.delenv("SM_TRACKER_TEST_ENV", raising=False)

    load_env_file(env_file)

    assert "hello" == os.environ["SM_TRACKER_TEST_ENV"]


def test_read_env_file_prefers_dotenv_over_existing_environment(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC=2026-08-20T01:20:16Z\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", "2026-06-21T07:56:43Z")

    env = read_env_file(env_file)

    assert env["THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC"] == "2026-08-20T01:20:16Z"


def test_load_env_file_overrides_stale_environment_value(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC=2026-08-20T01:20:16Z\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", "2026-06-21T07:56:43Z")

    load_env_file(env_file)

    assert os.environ["THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC"] == "2026-08-20T01:20:16Z"


def test_load_config_uses_env_next_to_explicit_config_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    app_dir = tmp_path / "sm-tracker"
    app_dir.mkdir()
    config_file = app_dir / "config.toml"
    config_file.write_text(
        (
            "[paths.dev]\n"
            'db = "./dev.db"\n'
            'logs = "./logs-dev"\n'
            "\n"
            "[logging.dev]\n"
            "retention_days = 7\n"
            'level = "INFO"\n'
        ),
        encoding="utf-8",
    )
    (app_dir / ".env").write_text(
        "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC=2026-08-20T01:20:16Z\n",
        encoding="utf-8",
    )
    run_dir = tmp_path / "daily-brief"
    run_dir.mkdir()
    monkeypatch.chdir(run_dir)
    monkeypatch.setenv("SM_TRACKER_CONFIG", str(config_file))
    monkeypatch.setenv("THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", "2026-06-21T07:56:43Z")

    config = load_config()

    assert config.env["THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC"] == "2026-08-20T01:20:16Z"


def test_resolve_profile_precedence(monkeypatch: pytest.MonkeyPatch) -> None:
    config = {"profile": "production"}

    monkeypatch.setenv("SM_TRACKER_PROFILE", "staging")
    assert "staging" == resolve_profile(config)
    assert "ci" == resolve_profile(config, profile_override="ci")


def test_load_config_with_profile_override(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        (
            'profile = "dev"\n'
            "\n"
            "[paths.dev]\n"
            'db = "./dev.db"\n'
            'logs = "./logs-dev"\n'
            "\n"
            "[paths.production]\n"
            'db = "./prod.db"\n'
            'logs = "./logs-prod"\n'
            "\n"
            "[logging.dev]\n"
            "retention_days = 7\n"
            'level = "DEBUG"\n'
            "\n"
            "[logging.production]\n"
            "retention_days = 14\n"
            'level = "INFO"\n'
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("SM_TRACKER_PROFILE", "dev")

    config = load_config(profile_override="production", config_path=config_file)

    assert config.profile == "production"
    assert config.db_path == Path("./prod.db")
    assert config.logs_path == Path("./logs-prod")
    assert config.log_retention_days == 14
    assert config.log_level == "INFO"


def test_load_config_missing_file_raises(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing-config.toml"
    with pytest.raises(ConfigError, match="Config file not found"):
        load_config(config_path=missing_path)


def test_load_config_invalid_profile_logging_raises(tmp_path: Path) -> None:
    config_file = tmp_path / "config.toml"
    config_file.write_text(
        (
            "[paths.dev]\n"
            'db = "./dev.db"\n'
            'logs = "./logs-dev"\n'
            "\n"
            "[logging.dev]\n"
            "retention_days = 0\n"
            'level = "INFO"\n'
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigError, match="positive integer"):
        load_config(config_path=config_file)
