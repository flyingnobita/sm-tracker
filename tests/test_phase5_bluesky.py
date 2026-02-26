"""Phase 5 Bluesky adapter and CLI flow tests."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.bluesky import BlueskyAdapter, create_bluesky_adapter


class _FakeClient:
    def __init__(self, profile: object) -> None:
        self.profile = profile
        self.login_calls: list[tuple[str, str]] = []

    def login(self, identifier: str, password: str) -> None:
        self.login_calls.append((identifier, password))

    def get_profile(self, *, actor: str) -> object:
        _ = actor
        return self.profile


def test_create_bluesky_adapter_requires_handle() -> None:
    try:
        create_bluesky_adapter({})
    except AdapterConfigError as exc:
        assert "missing BLUESKY_HANDLE" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing BLUESKY_HANDLE.")


def test_bluesky_adapter_fetch_counts_public_profile(monkeypatch: MonkeyPatch) -> None:
    adapter = BlueskyAdapter(handle="alice.bsky.social")
    fake_client = _FakeClient(
        profile=SimpleNamespace(followers_count=132, follows_count=47),
    )
    monkeypatch.setattr(
        BlueskyAdapter,
        "_build_client",
        lambda _self: fake_client,
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "bluesky"
    assert counts.follower_count == 132
    assert counts.following_count == 47
    assert fake_client.login_calls == []


def test_bluesky_adapter_logs_in_when_app_password_present(monkeypatch: MonkeyPatch) -> None:
    adapter = BlueskyAdapter(handle="alice.bsky.social", app_password="pw")
    fake_client = _FakeClient(profile={"followersCount": 8, "followsCount": 3})
    monkeypatch.setattr(
        BlueskyAdapter,
        "_build_client",
        lambda _self: fake_client,
    )

    counts = adapter.fetch_counts()

    assert counts.follower_count == 8
    assert counts.following_count == 3
    assert fake_client.login_calls == [("alice.bsky.social", "pw")]


def test_track_and_show_bluesky_end_to_end(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    runner = CliRunner()
    env = {"BLUESKY_HANDLE": "alice.bsky.social"}
    profile_sequence = iter(
        [
            SimpleNamespace(followers_count=100, follows_count=25),
            SimpleNamespace(followers_count=108, follows_count=30),
        ]
    )

    monkeypatch.setattr(
        BlueskyAdapter,
        "_build_client",
        lambda _self: _FakeClient(next(profile_sequence)),
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

        first_track = runner.invoke(app, ["track", "-p", "bluesky"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "bluesky"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "bluesky"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "bluesky"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: bluesky" in first_track.stdout
    assert "Tracking snapshot for: bluesky" in second_track.stdout
    assert "bluesky" in show_result.stdout
    assert "Followers: 108 (+8)" in show_result.stdout
    assert "Following: 30 (+5)" in show_result.stdout
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout
    assert "bluesky" in history_result.stdout


def test_bluesky_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Bluesky credentials against the real API."""
    handle = os.getenv("BLUESKY_HANDLE", "").strip()
    app_password = os.getenv("BLUESKY_APP_PASSWORD", "").strip()
    if not handle or not app_password:
        pytest.skip("Set BLUESKY_HANDLE and BLUESKY_APP_PASSWORD to run live Bluesky test.")

    adapter = BlueskyAdapter(handle=handle, app_password=app_password)
    counts = adapter.fetch_counts()

    assert counts.platform == "bluesky"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is None or counts.following_count >= 0
