"""Command to show historical snapshots."""

from __future__ import annotations

import logging

import typer

from sm_tracker.cli.app import app
from sm_tracker.cli.auth import warn_threads_token_expiry_if_needed
from sm_tracker.cli.formatters import _format_rows_csv, _format_rows_json, _history_rows_with_deltas
from sm_tracker.cli.options import (
    ALL_OPTION,
    OUTPUT_CSV_OPTION,
    OUTPUT_JSON_OPTION,
    PLATFORM_OPTION,
    _resolve_output_mode,
    _selected_platforms,
)
from sm_tracker.config import ConfigError, load_config
from sm_tracker.db import fetch_history, init_schema
from sm_tracker.db.connection import connect

LOGGER = logging.getLogger(__name__)


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
    selected_set = set(selected)
    LOGGER.info("history command started selected_platforms=%s limit=%s", selected, limit)

    try:
        config = load_config()
    except ConfigError as exc:
        LOGGER.warning("history command aborted: %s", exc)
        typer.echo(f"Could not load configuration: {exc}")
        return

    warn_threads_token_expiry_if_needed(selected, env=config.env)

    with connect(config.db_path) as client:
        try:
            init_schema(client)
        except Exception:  # pragma: no cover
            LOGGER.exception("history command failed to initialize database")
            typer.echo("Failed to initialize database. Check logs for details.")
            return

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

    structured_rows = _history_rows_with_deltas(rows)
    typer.echo("Date | Platform | Followers | Following | Delta")
    for s_row in structured_rows:
        followers = "N/A" if s_row["follower_count"] is None else str(s_row["follower_count"])
        following = "N/A" if s_row["following_count"] is None else str(s_row["following_count"])
        delta = s_row["follower_delta"]
        typer.echo(
            f"{s_row['snapshot_timestamp']} | {s_row['platform']} | "
            f"{followers} | {following} | {delta}"
        )
    LOGGER.info("history command finished rows_rendered=%s", len(rows))
