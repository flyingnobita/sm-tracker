"""Phase 4 CLI skeleton tests."""

import re

from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app


def _normalize_terminal_output(text: str) -> str:
    """Strip ANSI codes and collapse whitespace for stable CLI assertions."""
    without_ansi = re.sub(r"\x1b\[[0-9;]*m", "", text)
    return " ".join(without_ansi.split())


def test_cli_root_help_lists_expected_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "track" in result.stdout
    assert "show" in result.stdout
    assert "history" in result.stdout
    assert "config" in result.stdout
    assert "help" in result.stdout


def test_track_platform_flag_is_repeatable(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sm_tracker.cli.track.resolve_adapters", lambda _platforms, env=None: ([], [])
    )
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["track", "-p", "twitter", "--platform", "bluesky"],
        env={},
    )

    assert result.exit_code == 0
    assert "Tracking snapshot for: twitter, bluesky" in result.stdout


def test_track_rejects_unknown_platform() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["track", "-p", "unknownplatform"], env={})

    assert result.exit_code != 0
    assert "Unknown platform 'unknownplatform'" in result.output


def test_track_all_scope_targets_supported_platforms(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sm_tracker.cli.track.resolve_adapters", lambda _platforms, env=None: ([], [])
    )
    runner = CliRunner()
    result = runner.invoke(app, ["track", "--all"], env={})

    assert result.exit_code == 0
    assert (
        "Tracking snapshot for: bluesky, facebook, farcaster, mastodon, threads, twitter"
        in result.stdout
    )


def test_scope_flags_are_mutually_exclusive() -> None:
    runner = CliRunner()

    track_result = runner.invoke(app, ["track", "--all", "--platform", "twitter"], env={})
    show_result = runner.invoke(app, ["show", "--all", "--platform", "twitter"], env={})
    history_result = runner.invoke(app, ["history", "--all", "--platform", "twitter"], env={})

    assert track_result.exit_code != 0
    assert show_result.exit_code != 0
    assert history_result.exit_code != 0
    assert "Use either --platform or --all, not both." in _normalize_terminal_output(
        track_result.output
    )
    assert "Use either --platform or --all, not both." in _normalize_terminal_output(
        show_result.output
    )
    assert "Use either --platform or --all, not both." in _normalize_terminal_output(
        history_result.output
    )


def test_track_defaults_to_all_scope(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr(
        "sm_tracker.cli.track.resolve_adapters", lambda _platforms, env=None: ([], [])
    )
    runner = CliRunner()
    result = runner.invoke(app, ["track"], env={})

    assert result.exit_code == 0
    assert (
        "Tracking snapshot for: bluesky, facebook, farcaster, mastodon, threads, twitter"
        in result.stdout
    )


def test_show_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["show"])

    assert result.exit_code == 0
    assert "Could not load configuration:" in result.stdout


def test_history_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["history"])

    assert result.exit_code == 0
    assert "Could not load configuration:" in result.stdout


def test_show_all_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["show", "--all"])

    assert result.exit_code == 0
    assert "Could not load configuration:" in result.stdout


def test_history_all_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["history", "--all"])

    assert result.exit_code == 0
    assert "Could not load configuration:" in result.stdout


def test_command_help_describes_default_all_scope() -> None:
    runner = CliRunner()

    track_help = runner.invoke(app, ["track", "--help"])
    show_help = runner.invoke(app, ["show", "--help"])
    history_help = runner.invoke(app, ["history", "--help"])

    assert track_help.exit_code == 0
    assert show_help.exit_code == 0
    assert history_help.exit_code == 0
    normalized_track_help = _normalize_terminal_output(track_help.stdout)
    normalized_show_help = _normalize_terminal_output(show_help.stdout)
    normalized_history_help = _normalize_terminal_output(history_help.stdout)

    assert "Target platform(s)." in normalized_track_help
    assert "all platforms are targeted" in normalized_track_help
    assert "(same as --all)." in normalized_track_help

    assert "Target platform(s)." in normalized_show_help
    assert "(same as --all)." in normalized_show_help

    assert "Target platform(s)." in normalized_history_help
    assert "(same as --all)." in normalized_history_help


def test_help_command_outputs_usage() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "track" in result.stdout
