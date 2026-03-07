"""Configuration loading and validation helpers."""

from __future__ import annotations

import os
import tomllib
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

DEFAULT_PROFILE = "dev"
DEFAULT_DB_PATH = "~/.local/share/sm-tracker/data.db"
DEFAULT_LOGS_PATH = "~/.local/share/sm-tracker/logs"
DEFAULT_LOG_RETENTION_DAYS = 14
DEFAULT_LOG_LEVEL = "INFO"
SUPPORTED_LOG_LEVELS = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}


class ConfigError(ValueError):
    """Raised when config parsing or validation fails."""


@dataclass(frozen=True)
class AppConfig:
    """Fully resolved application configuration."""

    profile: str
    db_path: Path
    logs_path: Path
    log_retention_days: int
    log_level: str
    config_path: Path
    env: dict[str, str]


def read_env_file(env_path: Path | None = None) -> dict[str, str]:
    """Read `.env` variables without mutating os.environ directly, but merge with it."""
    from dotenv import dotenv_values

    path_to_read = env_path or Path.cwd() / ".env"
    env_vars = {}
    if path_to_read.exists():
        env_vars.update({k: v for k, v in dotenv_values(path_to_read).items() if v is not None})

    env_vars.update(dict(os.environ))
    return env_vars


def load_env_file(env_path: Path | None = None) -> None:
    """Load `.env` into process environment if present."""
    path_to_load = env_path or Path.cwd() / ".env"
    if path_to_load.exists():
        load_dotenv(dotenv_path=path_to_load, override=False)


def resolve_profile(config_data: Mapping[str, Any], profile_override: str | None = None) -> str:
    """Resolve active profile from CLI override, env var, then config default."""
    if profile_override:
        return profile_override

    profile_from_env = os.getenv("SM_TRACKER_PROFILE")
    if profile_from_env:
        return profile_from_env

    profile_from_config = config_data.get("profile")
    if isinstance(profile_from_config, str) and profile_from_config.strip():
        return profile_from_config

    return DEFAULT_PROFILE


def find_config_file(project_dir: Path | None = None) -> Path:
    """Locate `config.toml` via SM_TRACKER_CONFIG env var, project dir, then user config directory."""
    env_config = os.environ.get("SM_TRACKER_CONFIG")
    if env_config:
        p = Path(env_config).expanduser()
        if p.exists():
            return p
        raise ConfigError(f"Config file set by SM_TRACKER_CONFIG not found: {p}")

    cwd = (project_dir or Path.cwd()).expanduser()
    project_config = cwd / "config.toml"
    if project_config.exists():
        return project_config

    xdg_config_home = os.environ.get("XDG_CONFIG_HOME", "~/.config")
    user_config = Path(xdg_config_home).expanduser() / "sm-tracker" / "config.toml"
    if user_config.exists():
        return user_config

    raise ConfigError(f"Could not find config.toml in project directory or {user_config.parent}/.")


def _as_table(root: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    value = root.get(key)
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise ConfigError(f"Expected '{key}' to be a table in config.toml.")
    return value


def _resolve_path(value: str, fallback: str) -> Path:
    selected = value.strip() if value.strip() else fallback
    return Path(selected).expanduser()


def _resolve_profile_paths(config_data: Mapping[str, Any], profile: str) -> tuple[Path, Path]:
    paths_table = _as_table(config_data, "paths")
    profile_paths = paths_table.get(profile, {})
    if not isinstance(profile_paths, Mapping):
        raise ConfigError(f"Expected paths.{profile} to be a table in config.toml.")

    db_value = profile_paths.get("db", DEFAULT_DB_PATH)
    logs_value = profile_paths.get("logs", DEFAULT_LOGS_PATH)
    if not isinstance(db_value, str):
        raise ConfigError(f"Expected paths.{profile}.db to be a string in config.toml.")
    if not isinstance(logs_value, str):
        raise ConfigError(f"Expected paths.{profile}.logs to be a string in config.toml.")

    return _resolve_path(db_value, DEFAULT_DB_PATH), _resolve_path(logs_value, DEFAULT_LOGS_PATH)


def _resolve_profile_logging(config_data: Mapping[str, Any], profile: str) -> tuple[int, str]:
    logging_table = _as_table(config_data, "logging")
    profile_logging = logging_table.get(profile, {})
    if not isinstance(profile_logging, Mapping):
        raise ConfigError(f"Expected logging.{profile} to be a table in config.toml.")

    retention_days = profile_logging.get("retention_days", DEFAULT_LOG_RETENTION_DAYS)
    level = profile_logging.get("level", DEFAULT_LOG_LEVEL)

    if not isinstance(retention_days, int) or retention_days < 1:
        raise ConfigError(f"Expected logging.{profile}.retention_days to be a positive integer.")
    if not isinstance(level, str):
        raise ConfigError(f"Expected logging.{profile}.level to be a string.")

    normalized_level = level.upper()
    if normalized_level not in SUPPORTED_LOG_LEVELS:
        allowed = ", ".join(sorted(SUPPORTED_LOG_LEVELS))
        raise ConfigError(f"Unsupported log level '{level}'. Allowed: {allowed}.")

    return retention_days, normalized_level


def load_config(
    profile_override: str | None = None,
    config_path: Path | None = None,
    env_path: Path | None = None,
) -> AppConfig:
    """Load `.env`, parse `config.toml`, and return resolved app config."""
    load_env_file(env_path=env_path)
    env_vars = read_env_file(env_path=env_path)

    resolved_config_path = config_path or find_config_file()
    if not resolved_config_path.exists():
        raise ConfigError(f"Config file not found: {resolved_config_path}")

    try:
        raw_data = resolved_config_path.read_bytes()
        parsed = tomllib.loads(raw_data.decode("utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"Invalid TOML in {resolved_config_path}: {exc}") from exc

    if not isinstance(parsed, Mapping):
        raise ConfigError("Expected config.toml to contain a top-level table.")

    profile = resolve_profile(parsed, profile_override=profile_override)
    db_path, logs_path = _resolve_profile_paths(parsed, profile=profile)
    retention_days, log_level = _resolve_profile_logging(parsed, profile=profile)

    return AppConfig(
        profile=profile,
        db_path=db_path,
        logs_path=logs_path,
        log_retention_days=retention_days,
        log_level=log_level,
        config_path=resolved_config_path,
        env=env_vars,
    )
