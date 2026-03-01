"""Live integration test for the Meta auth command."""

from __future__ import annotations

import os

import pytest
from dotenv import load_dotenv
from typer.testing import CliRunner

from sm_tracker.cli import app


@pytest.mark.integration
def test_live_meta_auth_instagram() -> None:
    load_dotenv()
    app_id = os.environ.get("META_APP_ID", "").strip()
    app_secret = os.environ.get("META_APP_SECRET", "").strip()
    short_token = os.environ.get("META_USER_TOKEN_SHORT_LIVED", "").strip()

    if not all([app_id, app_secret, short_token]):
        pytest.skip("META_APP_ID, META_APP_SECRET, and META_USER_TOKEN_SHORT_LIVED not set")

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--platform", "instagram"])

    print("Output for instagram auth:")
    print(result.stdout)

    if result.exit_code != 0:
        pytest.fail(f"Auth command failed: {result.stdout}")

    assert result.exit_code == 0
    assert "Got long-lived user token successfully" in result.stdout
    assert "Saved LONG_LIVED_USER_TOKEN" in result.stdout


@pytest.mark.integration
def test_live_meta_auth_facebook() -> None:
    load_dotenv()
    app_id = os.environ.get("META_APP_ID", "").strip()
    app_secret = os.environ.get("META_APP_SECRET", "").strip()
    short_token = os.environ.get("META_USER_TOKEN_SHORT_LIVED", "").strip()

    if not all([app_id, app_secret, short_token]):
        pytest.skip("META_APP_ID, META_APP_SECRET, and META_USER_TOKEN_SHORT_LIVED not set")

    runner = CliRunner()
    result = runner.invoke(app, ["auth", "--platform", "facebook"])

    print("Output for facebook auth:")
    print(result.stdout)

    if result.exit_code != 0:
        pytest.fail(f"Auth command failed: {result.stdout}")

    assert result.exit_code == 0
    assert "Got long-lived user token successfully" in result.stdout
    assert "Fetching long-lived page tokens" in result.stdout
    assert "Saved FACEBOOK_PAGE_ACCESS_TOKEN" in result.stdout
