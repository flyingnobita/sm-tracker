"""Command to fetch counts and persist a snapshot."""

from __future__ import annotations

import logging

import typer

from sm_tracker.cli.app import app
from sm_tracker.cli.auth import warn_threads_token_expiry_if_needed
from sm_tracker.cli.formatters import _format_rows_csv, _format_rows_json, _show_rows_with_deltas
from sm_tracker.cli.options import (
    ALL_OPTION,
    OUTPUT_CSV_OPTION,
    OUTPUT_JSON_OPTION,
    PLATFORM_OPTION,
    _resolve_output_mode,
    _selected_platforms,
)
from sm_tracker.config import ConfigError, load_config
from sm_tracker.db import fetch_latest, init_schema, insert_count, insert_snapshot
from sm_tracker.db.connection import connect
from sm_tracker.db.queries import CountRow
from sm_tracker.platforms import SUPPORTED_PLATFORM_NAMES, resolve_adapters

LOGGER = logging.getLogger(__name__)


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
    LOGGER.info("track command started selected_platforms=%s", selected)

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.error("track command failed to load config: %s", exc)
        typer.echo(f"Could not load config: {exc}")
        return

    warn_threads_token_expiry_if_needed(selected, env=config.env)

    adapters, warnings = resolve_adapters(selected, env=config.env)
    for warning in warnings:
        LOGGER.warning("%s", warning)
        typer.echo(warning)

    if not adapters:
        LOGGER.info("track command finished with no adapters selected_platforms=%s", selected)
        typer.echo(f"Tracking snapshot for: {', '.join(selected)}")
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
