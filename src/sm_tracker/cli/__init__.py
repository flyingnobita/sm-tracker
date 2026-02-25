"""CLI package for sm-tracker."""

import typer

app = typer.Typer(
    help="Track follower and following counts across social media platforms.",
    no_args_is_help=True,
)


@app.callback()
def root() -> None:
    """Root command group for sm-tracker."""

