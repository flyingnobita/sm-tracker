"""CLI package for sm-tracker."""

from __future__ import annotations

import csv
import json
import logging
import os
import tomllib
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from io import StringIO
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import typer
from dotenv import dotenv_values, load_dotenv
from threads import ThreadsClient
from threads.constants import Scope

from sm_tracker.config import (
    DEFAULT_DB_PATH,
    DEFAULT_LOG_LEVEL,
    DEFAULT_LOG_RETENTION_DAYS,
    DEFAULT_LOGS_PATH,
    SUPPORTED_LOG_LEVELS,
    ConfigError,
    load_config,
)
from sm_tracker.db import (
    fetch_history,
    fetch_latest,
    init_schema,
    insert_count,
    insert_snapshot,
)
from sm_tracker.db.connection import connect
from sm_tracker.db.queries import CountRow
from sm_tracker.logging import setup_logging
from sm_tracker.platforms import SUPPORTED_PLATFORM_NAMES, resolve_adapters

app = typer.Typer(
    help="Track follower and following counts across social media platforms.",
    no_args_is_help=True,
)
LOGGER = logging.getLogger("sm_tracker.cli")

_AUTH_SUPPORTED_PLATFORMS: frozenset[str] = frozenset({"threads"})

ENV_FIELD_SPECS: list[tuple[str, str, bool]] = [
    ("TWITTER_BEARER_TOKEN", "Twitter bearer token", True),
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
    ("YOUTUBE_API_KEY", "YouTube API key", True),
    ("YOUTUBE_CHANNEL_ID", "YouTube channel ID (optional if handle provided)", False),
    ("YOUTUBE_HANDLE", "YouTube handle (optional if channel ID provided)", False),
]


@app.callback()
def root() -> None:
    """Root command group for sm-tracker."""
    _try_setup_logging()


def _try_setup_logging() -> None:
    """Best-effort logging bootstrap from app config."""
    try:
        config = load_config()
    except ConfigError:
        return

    setup_logging(
        logs_path=config.logs_path,
        level=config.log_level,
        retention_days=config.log_retention_days,
    )
    LOGGER.info(
        "CLI logging initialized for profile=%s db_path=%s logs_path=%s",
        config.profile,
        config.db_path,
        config.logs_path,
    )


def _normalized_platforms(platform: Sequence[str]) -> list[str]:
    return [name.strip().lower() for name in platform if name.strip()]


PLATFORM_OPTION = typer.Option(
    None,
    "--platform",
    "-p",
    help=(
        "Target platform(s). Repeat option to pass multiple values. "
        "If omitted, all platforms are targeted (same as --all)."
    ),
)
ALL_OPTION = typer.Option(
    False,
    "--all",
    help="Target all supported platforms (same as omitting --platform).",
)


def _selected_platforms(platform: Sequence[str], all_platforms: bool) -> list[str]:
    selected = _normalized_platforms(platform)
    if all_platforms and selected:
        raise typer.BadParameter("Use either --platform or --all, not both.")
    if all_platforms:
        return list(SUPPORTED_PLATFORM_NAMES)
    for name in selected:
        if name not in SUPPORTED_PLATFORM_NAMES:
            supported = ", ".join(SUPPORTED_PLATFORM_NAMES)
            raise typer.BadParameter(f"Unknown platform '{name}'. Supported: {supported}.")
    return selected


OUTPUT_JSON_OPTION = typer.Option(
    False,
    "--json",
    help="Output results as JSON.",
)
OUTPUT_CSV_OPTION = typer.Option(
    False,
    "--csv",
    help="Output results as CSV.",
)


def _resolve_output_mode(as_json: bool, as_csv: bool) -> str:
    if as_json and as_csv:
        raise typer.BadParameter("Use either --json or --csv, not both.")
    if as_json:
        return "json"
    if as_csv:
        return "csv"
    return "text"


@app.command()
def track(
    platform: list[str] | None = PLATFORM_OPTION,
    all_platforms: bool = ALL_OPTION,
    as_json: bool = OUTPUT_JSON_OPTION,
    as_csv: bool = OUTPUT_CSV_OPTION,
) -> None:
    """Fetch counts and persist a snapshot."""
    selected = _selected_platforms(platform or [], all_platforms)
    output_mode = _resolve_output_mode(as_json, as_csv)
    if not selected:
        selected = list(SUPPORTED_PLATFORM_NAMES)
    _warn_threads_token_expiry_if_needed(selected)
    LOGGER.info("track command started selected_platforms=%s", selected)

    adapters, warnings = resolve_adapters(selected)
    for warning in warnings:
        LOGGER.warning("%s", warning)
        typer.echo(warning)

    if not adapters:
        LOGGER.info("track command finished with no adapters selected_platforms=%s", selected)
        typer.echo(f"Tracking snapshot for: {', '.join(selected)}")
        return

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.error("track command failed to load config: %s", exc)
        typer.echo(f"Could not load config: {exc}")
        return

    successful_platforms: list[str] = []
    successful_counts: list[CountRow] = []
    successful = 0
    snapshot_id: int | None = None
    with connect(config.db_path) as client:
        try:
            init_schema(client)
            snapshot_id = insert_snapshot(client)
        except Exception:  # pragma: no cover - defensive branch
            LOGGER.exception("track command failed to initialize database")
            typer.echo("Failed to initialize database. Check logs for details.")
            return

        for adapter in adapters:
            try:
                counts = adapter.fetch_counts()
            except Exception:  # pragma: no cover - defensive branch
                LOGGER.exception("Skipping %s: fetch failed", adapter.name)
                typer.echo(f"Skipping {adapter.name}: fetch failed. Check logs for details.")
                continue

            try:
                insert_count(
                    client,
                    snapshot_id=snapshot_id,
                    platform=counts.platform,
                    follower_count=counts.follower_count,
                    following_count=counts.following_count,
                )
            except Exception:  # pragma: no cover - defensive branch
                LOGGER.exception("Skipping %s: failed to save counts", adapter.name)
                typer.echo(
                    f"Skipping {adapter.name}: failed to save counts. Check logs for details."
                )
                continue

            successful += 1
            successful_platforms.append(counts.platform)
            successful_counts.append(
                CountRow(
                    snapshot_id=snapshot_id,
                    timestamp="",
                    platform=counts.platform,
                    follower_count=counts.follower_count,
                    following_count=counts.following_count,
                )
            )
            LOGGER.info(
                "captured counts platform=%s followers=%s following=%s",
                counts.platform,
                counts.follower_count,
                counts.following_count,
            )

        if successful > 0 and output_mode != "text":
            latest_rows = fetch_latest(client)
            successful_platform_set = set(successful_platforms)
            successful_counts = [
                row for row in latest_rows if row.platform in successful_platform_set
            ]

    if successful == 0:
        LOGGER.warning("track command completed with zero successful adapter fetches")
        typer.echo("No platform data captured.")
        return

    if output_mode == "json":
        typer.echo(_format_rows_json(_show_rows_with_deltas(successful_counts, {})))
        return
    if output_mode == "csv":
        typer.echo(_format_rows_csv(_show_rows_with_deltas(successful_counts, {})).rstrip("\n"))
        return

    LOGGER.info("track command finished tracked_platforms=%s", successful_platforms)
    typer.echo(f"Tracking snapshot for: {', '.join(successful_platforms)}")


@app.command()
def show(
    platform: list[str] | None = PLATFORM_OPTION,
    all_platforms: bool = ALL_OPTION,
    as_json: bool = OUTPUT_JSON_OPTION,
    as_csv: bool = OUTPUT_CSV_OPTION,
) -> None:
    """Show latest snapshot with deltas."""
    selected = _selected_platforms(platform or [], all_platforms)
    output_mode = _resolve_output_mode(as_json, as_csv)
    _warn_threads_token_expiry_if_needed(selected)
    selected_set = set(selected)
    LOGGER.info("show command started selected_platforms=%s", selected)

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.warning("show command aborted: %s", exc)
        typer.echo(f"Could not load configuration: {exc}")
        return

    with connect(config.db_path) as client:
        init_schema(client)
        latest = fetch_latest(client)
        if not latest:
            LOGGER.info("show command: no snapshots found")
            typer.echo("No snapshots yet. Run `sm-tracker track` first.")
            return

        if selected_set:
            latest = [row for row in latest if row.platform in selected_set]
            if not latest:
                LOGGER.info("show command: selected platforms have no snapshot rows")
                typer.echo("No snapshots yet. Run `sm-tracker track` first.")
                return

        history = fetch_history(client)

    previous_by_platform = _previous_rows_by_platform(
        history,
        latest_snapshot_id=latest[0].snapshot_id,
    )
    if output_mode == "json":
        typer.echo(_format_rows_json(_show_rows_with_deltas(latest, previous_by_platform)))
        LOGGER.info("show command finished rows_rendered=%s", len(latest))
        return
    if output_mode == "csv":
        show_rows = _show_rows_with_deltas(latest, previous_by_platform)
        typer.echo(_format_rows_csv(show_rows).rstrip("\n"))
        LOGGER.info("show command finished rows_rendered=%s", len(latest))
        return

    for row in latest:
        previous = previous_by_platform.get(row.platform)
        follower_delta = _format_delta(
            row.follower_count,
            previous.follower_count if previous else None,
        )
        following_delta = _format_delta(
            row.following_count,
            previous.following_count if previous else None,
        )
        followers = _format_count_with_delta(row.follower_count, follower_delta)
        following = _format_count_with_delta(row.following_count, following_delta)
        typer.echo(f"{row.platform}")
        typer.echo(f"  Followers: {followers}")
        typer.echo(f"  Following: {following}")
    LOGGER.info("show command finished rows_rendered=%s", len(latest))


@app.command()
def history(
    platform: list[str] | None = PLATFORM_OPTION,
    all_platforms: bool = ALL_OPTION,
    limit: int = typer.Option(20, min=1, help="Maximum rows to print."),
    as_json: bool = OUTPUT_JSON_OPTION,
    as_csv: bool = OUTPUT_CSV_OPTION,
) -> None:
    """Show historical snapshots."""
    if limit < 1:
        typer.echo("--limit must be at least 1.")
        raise typer.Exit(code=1)
    selected = _selected_platforms(platform or [], all_platforms)
    output_mode = _resolve_output_mode(as_json, as_csv)
    _warn_threads_token_expiry_if_needed(selected)
    selected_set = set(selected)
    LOGGER.info("history command started selected_platforms=%s limit=%s", selected, limit)

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.warning("history command aborted: %s", exc)
        typer.echo(f"Could not load configuration: {exc}")
        return

    with connect(config.db_path) as client:
        init_schema(client)
        rows = fetch_history(client, limit=limit)

    if selected_set:
        rows = [row for row in rows if row.platform in selected_set]

    if not rows:
        LOGGER.info("history command: no rows available after filtering")
        typer.echo("No history yet. Run `sm-tracker track` first.")
        return

    if output_mode == "json":
        typer.echo(_format_rows_json(_history_rows_with_deltas(rows)))
        LOGGER.info("history command finished rows_rendered=%s", len(rows))
        return
    if output_mode == "csv":
        history_rows = _history_rows_with_deltas(rows)
        typer.echo(_format_rows_csv(history_rows, history_mode=True).rstrip("\n"))
        LOGGER.info("history command finished rows_rendered=%s", len(rows))
        return

    deltas = _history_follower_deltas(rows)
    typer.echo("Date | Platform | Followers | Following | Delta")
    for row, delta in zip(rows, deltas, strict=False):
        followers = "N/A" if row.follower_count is None else str(row.follower_count)
        following = "N/A" if row.following_count is None else str(row.following_count)
        typer.echo(f"{row.timestamp} | {row.platform} | {followers} | {following} | {delta}")
    LOGGER.info("history command finished rows_rendered=%s", len(rows))


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


@app.command(name="auth")
def auth_command(
    platform: str = typer.Option(
        ...,
        "--platform",
        "-p",
        help="Target platform for auth flow (currently: threads).",
    ),
) -> None:
    """Run platform OAuth flow and save credentials to .env."""
    selected_platform = platform.strip().lower()
    if selected_platform not in _AUTH_SUPPORTED_PLATFORMS:
        supported = ", ".join(sorted(_AUTH_SUPPORTED_PLATFORMS))
        typer.echo(f"Unsupported auth platform: {platform}")
        typer.echo(f"Currently supported: {supported}")
        raise typer.Exit(code=1)

    load_dotenv()

    app_id = os.getenv("THREADS_APP_ID", "").strip()
    app_secret = os.getenv("THREADS_APP_SECRET", "").strip()
    redirect_uri = os.getenv("THREADS_REDIRECT_URI", "https://localhost/callback").strip()
    if not app_id or not app_secret:
        typer.echo(
            "Missing THREADS_APP_ID or THREADS_APP_SECRET in environment. "
            "Set them in your .env file."
        )
        raise typer.Exit(code=1)

    client = ThreadsClient(access_token="")
    try:
        auth_url = client.auth.get_authorization_url(
            client_id=app_id,
            redirect_uri=redirect_uri,
            scopes=[
                Scope.BASIC,
                Scope.CONTENT_PUBLISH,
                Scope.MANAGE_INSIGHTS,
                Scope.READ_REPLIES,
                Scope.MANAGE_REPLIES,
            ],
        )
        typer.echo(
            "Open this URL and authorize the app. "
            "You will be redirected to THREADS_REDIRECT_URI with a code."
        )
        typer.echo(f"Open this URL: {auth_url}")

        callback_url = typer.prompt("Paste the full callback URL").strip()
        code = _extract_threads_code_from_callback_url(callback_url)
        if not code:
            typer.echo("Could not extract authorization code from callback URL.")
            raise typer.Exit(code=1)

        short_token = client.auth.exchange_code(
            client_id=app_id,
            client_secret=app_secret,
            redirect_uri=redirect_uri,
            code=code,
        )
        typer.echo(f"User ID: {short_token.user_id}")

        long_token = client.auth.get_long_lived_token(
            client_secret=app_secret,
            short_lived_token=short_token.access_token,
        )
        expires_at_utc = datetime.now(UTC) + timedelta(seconds=int(long_token.expires_in))
        expires_at_iso = expires_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        typer.echo(f"Expires at (UTC): {expires_at_iso}")

        env_path = Path(".env")
        if not env_path.exists():
            typer.echo("Could not find .env in current working directory.")
            raise typer.Exit(code=1)

        _upsert_env_var(env_path, "THREADS_ACCESS_TOKEN", long_token.access_token)
        _upsert_env_var(env_path, "THREADS_USER_ID", str(short_token.user_id))
        _upsert_env_var(env_path, "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", expires_at_iso)
        typer.echo("Saved THREADS_ACCESS_TOKEN, THREADS_USER_ID, and expiry time to .env")
    finally:
        client.close()


@app.command(name="help")
def help_command(ctx: typer.Context) -> None:
    """Show command help."""
    root_ctx = ctx.parent if ctx.parent is not None else ctx
    typer.echo(root_ctx.get_help())


def _format_delta(current: int | None, previous: int | None) -> str:
    if current is None or previous is None:
        return "N/A"

    delta = current - previous
    if delta > 0:
        return f"+{delta}"
    if delta < 0:
        return str(delta)
    return "0"


def _format_count_with_delta(value: int | None, delta: str) -> str:
    if value is None:
        return "N/A"
    return f"{value} ({delta})"


def _previous_rows_by_platform(
    history: list[CountRow], *, latest_snapshot_id: int
) -> dict[str, CountRow]:
    previous: dict[str, CountRow] = {}
    for row in history:
        if row.snapshot_id == latest_snapshot_id:
            continue
        previous.setdefault(row.platform, row)
    return previous


def _history_follower_deltas(rows: list[CountRow]) -> list[str]:
    deltas: list[str] = ["N/A"] * len(rows)
    indexes_by_platform: dict[str, list[int]] = {}

    for idx, row in enumerate(rows):
        indexes_by_platform.setdefault(row.platform, []).append(idx)

    for platform_indexes in indexes_by_platform.values():
        for pos, current_index in enumerate(platform_indexes):
            older_index = platform_indexes[pos + 1] if pos + 1 < len(platform_indexes) else None
            previous = rows[older_index].follower_count if older_index is not None else None
            deltas[current_index] = _format_delta(rows[current_index].follower_count, previous)

    return deltas


def _history_rows_with_deltas(
    rows: list[CountRow],
) -> list[dict[str, str | int | None]]:
    deltas = _history_follower_deltas(rows)
    structured: list[dict[str, str | int | None]] = []
    for row, delta in zip(rows, deltas, strict=False):
        structured.append(
            {
                "snapshot_id": row.snapshot_id,
                "snapshot_timestamp": row.timestamp,
                "platform": row.platform,
                "follower_count": row.follower_count,
                "following_count": row.following_count,
                "follower_delta": delta,
                "following_delta": None,
            }
        )
    return structured


def _show_rows_with_deltas(
    latest: list[CountRow], previous_by_platform: Mapping[str, CountRow]
) -> list[dict[str, str | int | None]]:
    rows: list[dict[str, str | int | None]] = []
    for row in latest:
        previous = previous_by_platform.get(row.platform)
        rows.append(
            {
                "snapshot_id": row.snapshot_id,
                "snapshot_timestamp": row.timestamp,
                "platform": row.platform,
                "follower_count": row.follower_count,
                "following_count": row.following_count,
                "follower_delta": _format_delta(
                    row.follower_count,
                    previous.follower_count if previous else None,
                ),
                "following_delta": _format_delta(
                    row.following_count,
                    previous.following_count if previous else None,
                ),
            }
        )
    return rows


def _format_rows_json(rows: list[dict[str, str | int | None]]) -> str:
    return json.dumps(rows)


def _format_rows_csv(rows: list[dict[str, str | int | None]], *, history_mode: bool = False) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "snapshot_id",
            "timestamp" if history_mode else "snapshot_timestamp",
            "platform",
            "follower_count",
            "following_count",
            "follower_delta",
            "following_delta",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["snapshot_id"],
                row["snapshot_timestamp"],
                row["platform"],
                row["follower_count"] if row["follower_count"] is not None else "",
                row["following_count"] if row["following_count"] is not None else "",
                row["follower_delta"] if row["follower_delta"] is not None else "",
                row["following_delta"] if row["following_delta"] is not None else "",
            ]
        )
    return output.getvalue()


def _upsert_env_var(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[idx] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _collect_config_warnings(env_path: Path, config_path: Path) -> list[str]:
    warnings: list[str] = []
    env_values = _read_env_file(env_path)
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
    existing = _read_env_file(env_path)
    typer.echo("Configure .env values (press Enter to keep current value).")
    updated: dict[str, str] = dict(existing)

    for key, prompt, required in ENV_FIELD_SPECS:
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
            continue
        if required:
            updated.pop(key, None)
            continue
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
        parsed = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError:
        return "dev", "", "", 0, ""

    profile_raw = parsed.get("profile")
    profile = profile_raw if isinstance(profile_raw, str) and profile_raw.strip() else "dev"

    paths = parsed.get("paths", {})
    logging_table = parsed.get("logging", {})
    profile_paths = paths.get(profile, {}) if isinstance(paths, Mapping) else {}
    profile_logging = logging_table.get(profile, {}) if isinstance(logging_table, Mapping) else {}

    db = profile_paths.get("db", "") if isinstance(profile_paths, Mapping) else ""
    logs = profile_paths.get("logs", "") if isinstance(profile_paths, Mapping) else ""
    retention = (
        profile_logging.get("retention_days", 0) if isinstance(profile_logging, Mapping) else 0
    )
    level = profile_logging.get("level", "") if isinstance(profile_logging, Mapping) else ""
    resolved_db = db if isinstance(db, str) else ""
    resolved_logs = logs if isinstance(logs, str) else ""
    resolved_retention = retention if isinstance(retention, int) else 0
    resolved_level = level if isinstance(level, str) else ""

    return profile, resolved_db, resolved_logs, resolved_retention, resolved_level


def _write_env_file(env_path: Path, values: Mapping[str, str]) -> None:
    filtered_items = [(key, value) for key, value in values.items() if value.strip()]
    lines = [f"{key}={value}" for key, value in filtered_items]
    env_path.write_text("\n".join(lines) + ("\n" if lines else ""), encoding="utf-8")


def _read_env_file(env_path: Path) -> dict[str, str]:
    if not env_path.exists():
        return {}
    return {k: v for k, v in dotenv_values(env_path).items() if v is not None}


def _validate_required_env_values(env_values: Mapping[str, str]) -> list[str]:
    missing_by_platform: dict[str, list[str]] = {
        "twitter": ["TWITTER_BEARER_TOKEN", "TWITTER_HANDLE"],
        "bluesky": ["BLUESKY_HANDLE"],
        "farcaster": ["FARCASTER_API_KEY", "FARCASTER_USERNAME"],
        "mastodon": ["MASTODON_ACCESS_TOKEN", "MASTODON_INSTANCE"],
        "threads": ["THREADS_ACCESS_TOKEN", "THREADS_USER_ID"],
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


def _extract_threads_code_from_callback_url(callback_url: str) -> str:
    url = callback_url.strip()
    if not url:
        return ""
    if url.endswith("#_"):
        url = url[:-2]

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    code = query.get("code", [""])[0].strip()
    if not code and "code=" in url:
        # Fallback for malformed callback URL input.
        code = url.split("code=", maxsplit=1)[1].strip()
    if code.endswith("#_"):
        code = code[:-2]
    return code


def _warn_threads_token_expiry_if_needed(
    selected_platforms: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    now_utc: datetime | None = None,
) -> None:
    if "threads" not in set(selected_platforms):
        return

    env_map = os.environ if env is None else env
    raw_expiry = env_map.get("THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", "").strip()
    if not raw_expiry:
        return

    try:
        normalized = raw_expiry
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        expires_at = datetime.fromisoformat(normalized)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        else:
            expires_at = expires_at.astimezone(UTC)
    except ValueError:
        typer.echo(
            "Threads access token expiry is invalid. "
            "Run `sm-tracker auth -p threads` to refresh it."
        )
        return

    current_time = datetime.now(UTC) if now_utc is None else now_utc
    if expires_at <= current_time:
        typer.echo(
            "Threads access token is expired. Run `sm-tracker auth -p threads` to refresh it."
        )
        return

    if expires_at <= current_time + timedelta(days=7):
        typer.echo(
            f"Threads access token expires soon ({expires_at.isoformat()}). "
            "Run `sm-tracker auth -p threads` to refresh it."
        )
