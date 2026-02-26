"""Phase 6 Farcaster adapter and CLI flow tests."""

from __future__ import annotations

import os
from pathlib import Path

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.farcaster import FarcasterAdapter, create_farcaster_adapter


def test_create_farcaster_adapter_requires_api_key() -> None:
    try:
        create_farcaster_adapter({"FARCASTER_USERNAME": "alice"})
    except AdapterConfigError as exc:
        assert "missing FARCASTER_API_KEY" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing FARCASTER_API_KEY.")


def test_create_farcaster_adapter_requires_username() -> None:
    try:
        create_farcaster_adapter({"FARCASTER_API_KEY": "secret"})
    except AdapterConfigError as exc:
        assert "missing FARCASTER_USERNAME" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing FARCASTER_USERNAME.")


def test_create_farcaster_adapter_uses_legacy_mnemonic_fallback() -> None:
    adapter = create_farcaster_adapter(
        {
            "FARCASTER_MNEMONIC": "legacy-secret",
            "FARCASTER_USERNAME": "alice",
        }
    )
    assert adapter.api_key == "legacy-secret"


def test_farcaster_adapter_fetch_counts(monkeypatch: MonkeyPatch) -> None:
    adapter = FarcasterAdapter(username="alice", api_key="secret")
    monkeypatch.setattr(
        FarcasterAdapter,
        "_request_user_payload",
        lambda _self: {
            "result": {
                "user": {
                    "followerCount": 120,
                    "followingCount": 65,
                }
            }
        },
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "farcaster"
    assert counts.follower_count == 120
    assert counts.following_count == 65


def test_farcaster_adapter_builds_curl_like_request_headers() -> None:
    adapter = FarcasterAdapter(username="alice", api_key="secret")
    request = adapter._build_request()

    assert request.full_url.endswith("username=alice")
    assert request.get_header("Authorization") == "Bearer secret"
    assert request.get_header("User-agent") == "curl/8.7.1"


def test_track_and_show_farcaster_end_to_end(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _ = tmp_path
    runner = CliRunner()
    env = {
        "FARCASTER_API_KEY": "secret",
        "FARCASTER_USERNAME": "alice",
    }
    payload_sequence = iter(
        [
            {"result": {"user": {"followerCount": 45, "followingCount": 20}}},
            {"result": {"user": {"followerCount": 49, "followingCount": 21}}},
        ]
    )

    monkeypatch.setattr(
        FarcasterAdapter,
        "_request_user_payload",
        lambda _self: next(payload_sequence),
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

        first_track = runner.invoke(app, ["track", "-p", "farcaster"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "farcaster"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "farcaster"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "farcaster"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: farcaster" in first_track.stdout
    assert "Tracking snapshot for: farcaster" in second_track.stdout
    assert "farcaster" in show_result.stdout
    assert "Followers: 49 (+4)" in show_result.stdout
    assert "Following: 21 (+1)" in show_result.stdout
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout
    assert "farcaster" in history_result.stdout


def test_farcaster_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Farcaster credentials against the real API."""
    api_key = os.getenv("FARCASTER_API_KEY", "").strip()
    username = os.getenv("FARCASTER_USERNAME", "").strip()
    if not api_key or not username:
        pytest.skip("Set FARCASTER_API_KEY and FARCASTER_USERNAME to run live Farcaster test.")

    adapter = FarcasterAdapter(username=username, api_key=api_key)
    counts = adapter.fetch_counts()

    assert counts.platform == "farcaster"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is not None
    assert counts.following_count >= 0
