"""Command to show latest snapshot with deltas."""

from __future__ import annotations

import logging

import typer

from sm_tracker.cli.app import app
from sm_tracker.cli.auth import warn_threads_token_expiry_if_needed
from sm_tracker.cli.formatters import (
    _format_count_with_delta,
    _format_delta,
    _format_rows_csv,
    _format_rows_json,
    _previous_rows_by_platform,
    _show_rows_with_deltas,
)
from sm_tracker.cli.options import (
    ALL_OPTION,
    OUTPUT_CSV_OPTION,
    OUTPUT_JSON_OPTION,
    PLATFORM_OPTION,
    _resolve_output_mode,
    _selected_platforms,
)
from sm_tracker.config import ConfigError, load_config
from sm_tracker.db import fetch_history, fetch_latest, init_schema
from sm_tracker.db.connection import connect

LOGGER = logging.getLogger(__name__)


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
    selected_set = set(selected)
    LOGGER.info("show command started selected_platforms=%s", selected)

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.warning("show command aborted: %s", exc)
        typer.echo(f"Could not load configuration: {exc}", err=True)
        raise typer.Exit(code=1)

    warn_threads_token_expiry_if_needed(selected, env=config.env)

    with connect(config.db_path) as client:
        try:
            init_schema(client)
        except Exception:  # pragma: no cover
            LOGGER.exception("show command failed to initialize database")
            typer.echo("Failed to initialize database. Check logs for details.")
            return

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
