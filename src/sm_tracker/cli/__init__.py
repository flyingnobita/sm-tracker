"""CLI package for sm-tracker."""

from __future__ import annotations

import logging
import os
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import typer
from dotenv import load_dotenv
from threads import ThreadsClient
from threads.constants import Scope

from sm_tracker.config import ConfigError, load_config
from sm_tracker.db import fetch_history, fetch_latest, init_schema, insert_count, insert_snapshot
from sm_tracker.db.connection import connect
from sm_tracker.db.queries import CountRow
from sm_tracker.logging import setup_logging
from sm_tracker.platforms import resolve_adapters

app = typer.Typer(
    help="Track follower and following counts across social media platforms.",
    no_args_is_help=True,
)
LOGGER = logging.getLogger("sm_tracker.cli")


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
    help="Target platform(s). Repeat option to pass multiple values.",
)


@app.command()
def track(
    platform: list[str] | None = PLATFORM_OPTION,
) -> None:
    """Fetch counts and persist a snapshot."""
    selected = _normalized_platforms(platform or [])
    _warn_threads_token_expiry_if_needed(selected)
    LOGGER.info("track command started selected_platforms=%s", selected)
    if not selected:
        LOGGER.warning("track command aborted: no platforms selected")
        typer.echo("Add at least one platform via `sm-tracker config` or .env (credentials)")
        return

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
    successful = 0
    with connect(config.db_path) as client:
        init_schema(client)
        snapshot_id = insert_snapshot(client)
        for adapter in adapters:
            try:
                counts = adapter.fetch_counts()
            except Exception as exc:  # pragma: no cover - defensive branch
                LOGGER.exception("Skipping %s: fetch failed", adapter.name)
                typer.echo(f"Skipping {adapter.name}: fetch failed ({exc})")
                continue

            insert_count(
                client,
                snapshot_id=snapshot_id,
                platform=counts.platform,
                follower_count=counts.follower_count,
                following_count=counts.following_count,
            )
            successful += 1
            successful_platforms.append(counts.platform)
            LOGGER.info(
                "captured counts platform=%s followers=%s following=%s",
                counts.platform,
                counts.follower_count,
                counts.following_count,
            )

    if successful == 0:
        LOGGER.warning("track command completed with zero successful adapter fetches")
        typer.echo("No platform data captured.")
        return

    LOGGER.info("track command finished tracked_platforms=%s", successful_platforms)
    typer.echo(f"Tracking snapshot for: {', '.join(successful_platforms)}")


@app.command()
def show(
    platform: list[str] | None = PLATFORM_OPTION,
) -> None:
    """Show latest snapshot with deltas."""
    selected = _normalized_platforms(platform or [])
    _warn_threads_token_expiry_if_needed(selected)
    selected_set = set(selected)
    LOGGER.info("show command started selected_platforms=%s", selected)

    try:
        config = load_config()
    except ConfigError:
        LOGGER.warning("show command aborted: config unavailable")
        typer.echo("No snapshots yet. Run `sm-tracker track` first.")
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
    limit: int = typer.Option(20, min=1, help="Maximum rows to print."),
) -> None:
    """Show historical snapshots."""
    selected = _normalized_platforms(platform or [])
    _warn_threads_token_expiry_if_needed(selected)
    selected_set = set(selected)
    LOGGER.info("history command started selected_platforms=%s limit=%s", selected, limit)

    try:
        config = load_config()
    except ConfigError:
        LOGGER.warning("history command aborted: config unavailable")
        typer.echo("No history yet. Run `sm-tracker track` first.")
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
    typer.echo("Configuration wizard is not implemented yet.")


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
    if selected_platform != "threads":
        typer.echo(f"Unsupported auth platform: {platform}")
        typer.echo("Currently supported: threads")
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
        typer.echo(f"Short-lived token: {short_token.access_token}")
        typer.echo(f"User ID: {short_token.user_id}")

        long_token = client.auth.get_long_lived_token(
            client_secret=app_secret,
            short_lived_token=short_token.access_token,
        )
        expires_at_utc = datetime.now(UTC) + timedelta(seconds=int(long_token.expires_in))
        expires_at_iso = expires_at_utc.replace(microsecond=0).isoformat().replace("+00:00", "Z")
        typer.echo(f"Long-lived token: {long_token.access_token}")
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
