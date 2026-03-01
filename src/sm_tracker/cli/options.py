"""Common CLI options and argument parsers."""

from __future__ import annotations

from collections.abc import Sequence

import typer

from sm_tracker.platforms import SUPPORTED_PLATFORM_NAMES


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
