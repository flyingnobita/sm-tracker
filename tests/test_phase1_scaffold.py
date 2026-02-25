"""Phase 1 scaffold smoke tests."""

from typer.testing import CliRunner

from sm_tracker.cli import app


def test_package_imports() -> None:
    import sm_tracker
    import sm_tracker.config
    import sm_tracker.db
    import sm_tracker.logging
    import sm_tracker.platforms

    assert sm_tracker is not None
    assert sm_tracker.config is not None
    assert sm_tracker.db is not None
    assert sm_tracker.logging is not None
    assert sm_tracker.platforms is not None


def test_cli_app_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "Track follower and following counts" in result.stdout

