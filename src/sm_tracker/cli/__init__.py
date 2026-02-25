"""CLI package for sm-tracker."""

from collections.abc import Sequence

import typer

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

    typer.echo(f"Tracking snapshot for: {', '.join(selected)}")


@app.command()
def show(
    platform: list[str] | None = PLATFORM_OPTION,
) -> None:
    """Show latest snapshot with deltas."""
    _ = _normalized_platforms(platform or [])
    typer.echo("No snapshots yet. Run `sm-tracker track` first.")


@app.command()
def history(
    platform: list[str] | None = PLATFORM_OPTION,
    limit: int = typer.Option(20, min=1, help="Maximum rows to print."),
) -> None:
    """Show historical snapshots."""
    _ = _normalized_platforms(platform or [])
    _ = limit
    typer.echo("No history yet. Run `sm-tracker track` first.")


@app.command(name="config")
def config_command() -> None:
    """Guide credential and config setup."""
    typer.echo("Configuration wizard is not implemented yet.")


@app.command(name="help")
def help_command(ctx: typer.Context) -> None:
    """Show command help."""
    root_ctx = ctx.parent if ctx.parent is not None else ctx
    typer.echo(root_ctx.get_help())
