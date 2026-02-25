"""CLI package for sm-tracker."""

from __future__ import annotations

import logging
from collections.abc import Sequence

import typer

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

    tracked_platforms = [adapter.name for adapter in adapters]
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

    LOGGER.info("track command finished tracked_platforms=%s", tracked_platforms)
    typer.echo(f"Tracking snapshot for: {', '.join(tracked_platforms)}")


@app.command()
def show(
    platform: list[str] | None = PLATFORM_OPTION,
) -> None:
    """Show latest snapshot with deltas."""
    selected = _normalized_platforms(platform or [])
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

    typer.echo("Date | Platform | Followers | Following")
    for row in rows:
        followers = "N/A" if row.follower_count is None else str(row.follower_count)
        following = "N/A" if row.following_count is None else str(row.following_count)
        typer.echo(f"{row.timestamp} | {row.platform} | {followers} | {following}")
    LOGGER.info("history command finished rows_rendered=%s", len(rows))


@app.command(name="config")
def config_command() -> None:
    """Guide credential and config setup."""
    typer.echo("Configuration wizard is not implemented yet.")


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
