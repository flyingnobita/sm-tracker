"""CLI package for sm-tracker."""

from __future__ import annotations

from collections.abc import Sequence

import typer

from sm_tracker.config import ConfigError, load_config
from sm_tracker.db import fetch_history, fetch_latest, init_schema, insert_count, insert_snapshot
from sm_tracker.db.connection import connect
from sm_tracker.db.queries import CountRow
from sm_tracker.platforms import resolve_adapters

app = typer.Typer(
    help="Track follower and following counts across social media platforms.",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """Root command group for sm-tracker."""


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
    if not selected:
        typer.echo("Add at least one platform via `sm-tracker config` or .env (credentials)")
        return

    adapters, warnings = resolve_adapters(selected)
    for warning in warnings:
        typer.echo(warning)

    if not adapters:
        typer.echo(f"Tracking snapshot for: {', '.join(selected)}")
        return

    try:
        config = load_config()
    except ConfigError as exc:
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

    if successful == 0:
        typer.echo("No platform data captured.")
        return

    typer.echo(f"Tracking snapshot for: {', '.join(tracked_platforms)}")


@app.command()
def show(
    platform: list[str] | None = PLATFORM_OPTION,
) -> None:
    """Show latest snapshot with deltas."""
    selected = _normalized_platforms(platform or [])
    selected_set = set(selected)

    try:
        config = load_config()
    except ConfigError:
        typer.echo("No snapshots yet. Run `sm-tracker track` first.")
        return

    with connect(config.db_path) as client:
        init_schema(client)
        latest = fetch_latest(client)
        if not latest:
            typer.echo("No snapshots yet. Run `sm-tracker track` first.")
            return

        if selected_set:
            latest = [row for row in latest if row.platform in selected_set]
            if not latest:
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


@app.command()
def history(
    platform: list[str] | None = PLATFORM_OPTION,
    limit: int = typer.Option(20, min=1, help="Maximum rows to print."),
) -> None:
    """Show historical snapshots."""
    selected = _normalized_platforms(platform or [])
    selected_set = set(selected)

    try:
        config = load_config()
    except ConfigError:
        typer.echo("No history yet. Run `sm-tracker track` first.")
        return

    with connect(config.db_path) as client:
        init_schema(client)
        rows = fetch_history(client, limit=limit)

    if selected_set:
        rows = [row for row in rows if row.platform in selected_set]

    if not rows:
        typer.echo("No history yet. Run `sm-tracker track` first.")
        return

    typer.echo("Date | Platform | Followers | Following")
    for row in rows:
        followers = "N/A" if row.follower_count is None else str(row.follower_count)
        following = "N/A" if row.following_count is None else str(row.following_count)
        typer.echo(f"{row.timestamp} | {row.platform} | {followers} | {following}")


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
