"""CLI package main entry point for sm-tracker."""

from __future__ import annotations

import logging

import typer

from sm_tracker.config import ConfigError, load_config
from sm_tracker.logging import setup_logging

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

    try:
        setup_logging(
            logs_path=config.logs_path,
            level=config.log_level,
            retention_days=config.log_retention_days,
        )
    except OSError:
        return
    LOGGER.info(
        "CLI logging initialized for profile=%s db_path=%s logs_path=%s",
        config.profile,
        config.db_path,
        config.logs_path,
    )


@app.command(name="help")
def help_command(ctx: typer.Context) -> None:
    """Show command help."""
    root_ctx = ctx.parent if ctx.parent is not None else ctx
    typer.echo(root_ctx.get_help())
