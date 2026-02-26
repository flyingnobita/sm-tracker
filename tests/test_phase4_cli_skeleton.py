"""Phase 4 CLI skeleton tests."""

from typer.testing import CliRunner

from sm_tracker.cli import app


def test_cli_root_help_lists_expected_commands() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])

    assert result.exit_code == 0
    assert "track" in result.stdout
    assert "show" in result.stdout
    assert "history" in result.stdout
    assert "config" in result.stdout
    assert "help" in result.stdout


def test_track_platform_flag_is_repeatable() -> None:
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["track", "-p", "UnknownOne", "--platform", "unknown-two"],
        env={},
    )

    assert result.exit_code == 0
    assert "Skipping unsupported platform: unknownone" in result.stdout
    assert "Skipping unsupported platform: unknown-two" in result.stdout
    assert "Tracking snapshot for: unknownone, unknown-two" in result.stdout


def test_track_all_scope_targets_supported_platforms() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["track", "--all"], env={})

    assert result.exit_code == 0
    assert (
        "Tracking snapshot for: bluesky, farcaster, mastodon, threads, twitter"
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
    assert "Use either --platform or --all, not both." in track_result.output
    assert "Use either --platform or --all, not both." in show_result.output
    assert "Use either --platform or --all, not both." in history_result.output


def test_track_empty_state_message() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["track"])

    assert result.exit_code == 0
    assert (
        "Add at least one platform via `sm-tracker config` or .env (credentials)" in result.stdout
    )


def test_show_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["show"])

    assert result.exit_code == 0
    assert "No snapshots yet. Run `sm-tracker track` first." in result.stdout


def test_history_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["history"])

    assert result.exit_code == 0
    assert "No history yet. Run `sm-tracker track` first." in result.stdout


def test_show_all_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["show", "--all"])

    assert result.exit_code == 0
    assert "No snapshots yet. Run `sm-tracker track` first." in result.stdout


def test_history_all_empty_state_message() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["history", "--all"])

    assert result.exit_code == 0
    assert "No history yet. Run `sm-tracker track` first." in result.stdout


def test_help_command_outputs_usage() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["help"])

    assert result.exit_code == 0
    assert "Usage:" in result.stdout
    assert "track" in result.stdout
