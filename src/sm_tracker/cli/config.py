"""Command to run config wizard."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import typer

from sm_tracker.cli.app import app
from sm_tracker.config import (
    DEFAULT_DB_PATH,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_RETENTION_DAYS,
    DEFAULT_LOGS_PATH,
    SUPPORTED_LOG_LEVELS,
    ConfigError,
    load_config,
    read_env_file,
)

ENV_FIELD_SPECS: list[tuple[str, str, bool]] = [
    ("TWITTER_CONSUMER_KEY", "Twitter consumer key", True),
    ("TWITTER_CONSUMER_SECRET", "Twitter consumer secret", True),
    ("TWITTER_ACCESS_TOKEN", "Twitter access token", True),
    ("TWITTER_ACCESS_TOKEN_SECRET", "Twitter access token secret", True),
    ("TWITTER_HANDLE", "Twitter handle to track", True),
    ("BLUESKY_HANDLE", "Bluesky handle to track", True),
    ("BLUESKY_APP_PASSWORD", "Bluesky app password (optional)", False),
    ("FARCASTER_API_KEY", "Farcaster API key", True),
    ("FARCASTER_USERNAME", "Farcaster username to track", True),
    ("MASTODON_ACCESS_TOKEN", "Mastodon access token", True),
    ("MASTODON_INSTANCE", "Mastodon instance (for example mastodon.social)", True),
    ("THREADS_APP_ID", "Threads app ID (optional, needed for auth command)", False),
    (
        "THREADS_APP_SECRET",
        "Threads app secret (optional, needed for auth command)",
        False,
    ),
    ("THREADS_REDIRECT_URI", "Threads redirect URI", False),
    ("THREADS_ACCESS_TOKEN", "Threads access token", True),
    ("THREADS_USER_ID", "Threads user ID", True),
    (
        "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC",
        "Threads token expiry UTC (ISO, optional)",
        False,
    ),
    ("INSTAGRAM_ACCOUNT_ID", "Instagram account ID", True),
    ("LONG_LIVED_USER_TOKEN", "Instagram access token", True),
    ("FACEBOOK_ID", "Facebook ID", True),
    ("FACEBOOK_ACCESS_TOKEN", "Facebook user access token", True),
    ("FACEBOOK_PAGE_ACCESS_TOKEN", "Facebook page access token (optional)", False),
    ("META_APP_ID", "Meta App ID (for auth)", False),
    ("META_APP_SECRET", "Meta App Secret (for auth)", False),
    ("META_USER_TOKEN_SHORT_LIVED", "Meta Short-Lived User Token (for auth)", False),
    ("YOUTUBE_API_KEY", "YouTube API key", True),
    ("YOUTUBE_CHANNEL_ID", "YouTube channel ID (optional if handle provided)", False),
    ("YOUTUBE_HANDLE", "YouTube handle (optional if channel ID provided)", False),
]


@app.command(name="config")
def config_command() -> None:
    """Guide credential and config setup."""
    env_path = Path(".env")
    config_path = Path("config.toml")

    typer.echo("Guided setup for .env and config.toml")
    pre_warnings = _collect_config_warnings(env_path=env_path, config_path=config_path)
    if pre_warnings:
        typer.echo("Found existing configuration warnings:")
        for warning in pre_warnings:
            typer.echo(f"- {warning}")

    env_values = _run_env_wizard(env_path)
    _write_env_file(env_path, env_values)
    typer.echo(f"Updated {env_path}")

    profile, db_path, logs_path, retention_days, log_level = _run_config_wizard(config_path)
    _write_config_file(
        config_path=config_path,
        active_profile=profile,
        active_db_path=db_path,
        active_logs_path=logs_path,
        active_retention_days=retention_days,
        active_log_level=log_level,
    )
    typer.echo(f"Updated {config_path}")

    post_warnings = _collect_config_warnings(env_path=env_path, config_path=config_path)
    if post_warnings:
        typer.echo("Validation warnings:")
        for warning in post_warnings:
            typer.echo(f"- {warning}")
    else:
        typer.echo("Validation passed. Configuration looks good.")


def _collect_config_warnings(env_path: Path, config_path: Path) -> list[str]:
    warnings: list[str] = []
    env_values = read_env_file(env_path)
    if not env_path.exists():
        warnings.append(".env is missing and will be created.")
    warnings.extend(_validate_required_env_values(env_values))

    if not config_path.exists():
        warnings.append("config.toml is missing and will be created.")
    else:
        try:
            load_config(config_path=config_path, env_path=env_path)
        except ConfigError as exc:
            warnings.append(f"config.toml error: {exc}")

    return warnings


def _run_env_wizard(env_path: Path) -> dict[str, str]:
    existing = read_env_file(env_path)
    typer.echo("Configure .env values (press Enter to keep current value).")
    updated: dict[str, str] = dict(existing)

    for key, prompt, _required in ENV_FIELD_SPECS:
        current = existing.get(key, "")
        default_value = current
        if key == "THREADS_REDIRECT_URI" and not default_value:
            default_value = "https://localhost/callback"
        value = typer.prompt(
            prompt,
            default=default_value,
            show_default=bool(default_value),
        ).strip()
        if value:
            updated[key] = value
        else:
            updated.pop(key, None)

    return updated


def _run_config_wizard(config_path: Path) -> tuple[str, str, str, int, str]:
    existing_profile, existing_db, existing_logs, existing_retention, existing_level = (
        _read_existing_profile_settings(config_path)
    )
    typer.echo("Configure config.toml values.")

    profile = (
        typer.prompt(
            "Active profile (dev/production)",
            default=existing_profile,
            show_default=True,
        ).strip()
        or "dev"
    )
    if profile not in {"dev", "production"}:
        typer.echo("Unsupported profile value. Falling back to dev.")
        profile = "dev"

    default_db = existing_db or (DEFAULT_DB_PATH if profile == "production" else "./data-dev.db")
    default_logs = existing_logs or (DEFAULT_LOGS_PATH if profile == "production" else "./logs-dev")
    default_retention = (
        existing_retention
        if existing_retention > 0
        else (DEFAULT_LOG_RETENTION_DAYS if profile == "production" else 7)
    )
    default_level = existing_level or (DEFAULT_LOG_LEVEL if profile == "production" else "DEBUG")

    db_path = typer.prompt("Database path", default=default_db, show_default=True).strip()
    logs_path = typer.prompt("Log directory path", default=default_logs, show_default=True).strip()
    retention_days = typer.prompt(
        "Log retention days",
        default=str(default_retention),
        show_default=True,
    ).strip()
    level = typer.prompt(
        "Log level",
        default=default_level,
        show_default=True,
    ).strip()

    retention_int = (
        int(retention_days) if retention_days.isdigit() and int(retention_days) > 0 else 14
    )
    normalized_level = level.upper() if level else DEFAULT_LOG_LEVEL
    if normalized_level not in SUPPORTED_LOG_LEVELS:
        normalized_level = DEFAULT_LOG_LEVEL

    return profile, db_path, logs_path, retention_int, normalized_level


def _read_existing_profile_settings(
    config_path: Path,
) -> tuple[str, str, str, int, str]:
    if not config_path.exists():
        return "dev", "", "", 0, ""

    try:
        config = load_config(config_path=config_path)
        return (
            config.profile,
            str(config.db_path),
            str(config.logs_path),
            config.log_retention_days,
            config.log_level,
        )
    except ConfigError:
        return "dev", "", "", 0, ""


def _write_env_file(env_path: Path, values: Mapping[str, str]) -> None:
    filtered_items = [(key, value) for key, value in values.items() if value.strip()]
    lines = [f"{key}={value}" for key, value in filtered_items]
    env_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _validate_required_env_values(env_values: Mapping[str, str]) -> list[str]:
    missing_by_platform: dict[str, list[str]] = {
        "twitter": [
            "TWITTER_CONSUMER_KEY",
            "TWITTER_CONSUMER_SECRET",
            "TWITTER_ACCESS_TOKEN",
            "TWITTER_ACCESS_TOKEN_SECRET",
            "TWITTER_HANDLE",
        ],
        "bluesky": ["BLUESKY_HANDLE"],
        "farcaster": ["FARCASTER_API_KEY", "FARCASTER_USERNAME"],
        "mastodon": ["MASTODON_ACCESS_TOKEN", "MASTODON_INSTANCE"],
        "threads": ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"],
        "instagram": ["INSTAGRAM_ACCOUNT_ID", "LONG_LIVED_USER_TOKEN"],
        "facebook": ["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_ID"],
        "youtube": ["YOUTUBE_API_KEY"],
    }
    warnings: list[str] = []
    for platform, keys in missing_by_platform.items():
        missing = [key for key in keys if not env_values.get(key, "").strip()]

        if platform == "youtube":
            if (
                not env_values.get("YOUTUBE_CHANNEL_ID", "").strip()
                and not env_values.get("YOUTUBE_HANDLE", "").strip()
            ):
                missing.append("YOUTUBE_CHANNEL_ID or YOUTUBE_HANDLE")

        if missing:
            warnings.append(f"{platform}: missing {', '.join(missing)}")
    return warnings


def _write_config_file(
    *,
    config_path: Path,
    active_profile: str,
    active_db_path: str,
    active_logs_path: str,
    active_retention_days: int,
    active_log_level: str,
) -> None:
    defaults_by_profile: dict[str, tuple[str, str, int, str]] = {
        "dev": ("./data-dev.db", "./logs-dev", 7, "DEBUG"),
        "production": (DEFAULT_DB_PATH, DEFAULT_LOGS_PATH, 14, "INFO"),
    }

    dev_db, dev_logs, dev_retention, dev_level = defaults_by_profile["dev"]
    prod_db, prod_logs, prod_retention, prod_level = defaults_by_profile["production"]
    if active_profile == "dev":
        dev_db = active_db_path
        dev_logs = active_logs_path
        dev_retention = active_retention_days
        dev_level = active_log_level
    else:
        prod_db = active_db_path
        prod_logs = active_logs_path
        prod_retention = active_retention_days
        prod_level = active_log_level

    config_body = (
        f'profile = "{active_profile}"\n'
        "\n"
        "[paths.dev]\n"
        f'db = "{dev_db}"\n'
        f'logs = "{dev_logs}"\n'
        "\n"
        "[paths.production]\n"
        f'db = "{prod_db}"\n'
        f'logs = "{prod_logs}"\n'
        "\n"
        "[logging.dev]\n"
        f"retention_days = {dev_retention}\n"
        f'level = "{dev_level}"\n'
        "\n"
        "[logging.production]\n"
        f"retention_days = {prod_retention}\n"
        f'level = "{prod_level}"\n'
    )
    config_path.write_text(config_body, encoding="utf-8")
