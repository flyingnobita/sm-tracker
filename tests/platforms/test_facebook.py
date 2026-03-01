"""Phase 6 Facebook adapter and CLI flow tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.facebook import FacebookAdapter


def test_from_env_facebook_requires_access_token() -> None:
    try:
        FacebookAdapter.from_env({"FACEBOOK_ID": "12345"})
    except AdapterConfigError as exc:
        assert "missing FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing tokens.")


def test_from_env_facebook_requires_target_id() -> None:
    try:
        FacebookAdapter.from_env({"FACEBOOK_ACCESS_TOKEN": "secret"})
    except AdapterConfigError as exc:
        assert "FACEBOOK_ID is required when using FACEBOOK_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing FACEBOOK_ID.")


def test_facebook_adapter_fetch_counts_page(monkeypatch: MonkeyPatch) -> None:
    adapter = FacebookAdapter(target_id="12345", access_token="secret")
    monkeypatch.setattr(
        FacebookAdapter,
        "_request_graph_payload",
        lambda _self, _id, _token: {
            "id": "12345",
            "followers_count": 120,
            "fan_count": 115,  # fan_count usually means likes
        },
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "facebook"
    assert counts.follower_count == 120
    assert counts.following_count is None


def test_facebook_adapter_fetch_counts_group(monkeypatch: MonkeyPatch) -> None:
    adapter = FacebookAdapter(target_id="group123", access_token="secret")
    monkeypatch.setattr(
        FacebookAdapter,
        "_request_graph_payload",
        lambda _self, _id, _token: {
            "id": "group123",
            "member_count": 500,
        },
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "facebook"
    # member_count maps to follower_count for sm-tracker purposes
    assert counts.follower_count == 500
    assert counts.following_count is None


def test_track_and_show_facebook_end_to_end(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _ = tmp_path
    runner = CliRunner()
    env = {
        "FACEBOOK_ACCESS_TOKEN": "secret",
        "FACEBOOK_ID": "12345",
    }
    payload_sequence = iter(
        [
            {"id": "12345", "followers_count": 45},
            {"id": "12345", "followers_count": 49},
        ]
    )

    monkeypatch.setattr(
        FacebookAdapter,
        "from_env",
        classmethod(lambda cls, e: cls(target_id="12345", access_token="mock_page_token")),
    )

    monkeypatch.setattr(
        FacebookAdapter,
        "_request_graph_payload",
        lambda _self, _id, _token: next(payload_sequence),
    )
    with runner.isolated_filesystem():
        Path("config.toml").write_text(
            """
profile = "dev"

[paths.dev]
db = "./sm-tracker.db"
logs = "./logs"

[logging.dev]
retention_days = 7
level = "INFO"
""".strip()
            + "\n",
            encoding="utf-8",
        )

        first_track = runner.invoke(app, ["track", "-p", "facebook"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "facebook"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "facebook"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "facebook"], env=env)

    assert first_track.exit_code == 0, first_track.output
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: facebook" in first_track.stdout
    assert "facebook" in show_result.stdout
    assert "Followers: 49 (+4)" in show_result.stdout
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout


@pytest.mark.integration
def test_facebook_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Facebook credentials against the real API."""
    access_token = os.getenv("FACEBOOK_ACCESS_TOKEN", "").strip()
    target_id = os.getenv("FACEBOOK_ID", "").strip()
    if not access_token or not target_id:
        pytest.skip("Set FACEBOOK_ACCESS_TOKEN and FACEBOOK_ID to run live Facebook test.")

    adapter = FacebookAdapter(target_id=target_id, access_token=access_token)
    counts = adapter.fetch_counts()

    assert counts.platform == "facebook"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
