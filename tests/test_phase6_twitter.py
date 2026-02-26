"""Phase 6 Twitter adapter and CLI flow tests."""

from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.twitter import TwitterAdapter, create_twitter_adapter


class _FakeTwitterClient:
    def __init__(self, metrics: dict[str, Any]) -> None:
        self.metrics = metrics
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def get_user(self, *, username: str, user_fields: list[str]) -> object:
        self.calls.append((username, tuple(user_fields)))
        return SimpleNamespace(
            data=SimpleNamespace(public_metrics=self.metrics),
        )


def test_create_twitter_adapter_requires_bearer_token() -> None:
    try:
        create_twitter_adapter({"TWITTER_HANDLE": "alice"})
    except AdapterConfigError as exc:
        assert "missing TWITTER_BEARER_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_BEARER_TOKEN.")


def test_create_twitter_adapter_requires_handle() -> None:
    try:
        create_twitter_adapter({"TWITTER_BEARER_TOKEN": "token"})
    except AdapterConfigError as exc:
        assert "missing TWITTER_HANDLE" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_HANDLE.")


def test_twitter_adapter_fetch_counts(monkeypatch: MonkeyPatch) -> None:
    adapter = TwitterAdapter(handle="alice", bearer_token="token")
    fake_client = _FakeTwitterClient(metrics={"followers_count": 451, "following_count": 42})
    monkeypatch.setattr(
        TwitterAdapter,
        "_build_client",
        lambda _self: fake_client,
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "twitter"
    assert counts.follower_count == 451
    assert counts.following_count == 42
    assert fake_client.calls == [("alice", ("public_metrics",))]


def test_track_and_show_twitter_end_to_end(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "TWITTER_BEARER_TOKEN": "token",
        "TWITTER_HANDLE": "alice",
    }
    metrics_sequence = iter(
        [
            {"followers_count": 200, "following_count": 50},
            {"followers_count": 209, "following_count": 53},
        ]
    )

    monkeypatch.setattr(
        TwitterAdapter,
        "_build_client",
        lambda _self: _FakeTwitterClient(next(metrics_sequence)),
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

        first_track = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "twitter"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "twitter"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: twitter" in first_track.stdout
    assert "Tracking snapshot for: twitter" in second_track.stdout
    assert "twitter" in show_result.stdout
    assert "Followers: 209 (+9)" in show_result.stdout
    assert "Following: 53 (+3)" in show_result.stdout
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout
    assert "twitter" in history_result.stdout


def test_twitter_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Twitter credentials against the real API."""
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN", "").strip()
    handle = os.getenv("TWITTER_HANDLE", "").strip()
    if not bearer_token or not handle:
        pytest.skip("Set TWITTER_BEARER_TOKEN and TWITTER_HANDLE to run live Twitter test.")

    adapter = TwitterAdapter(handle=handle, bearer_token=bearer_token)
    counts = adapter.fetch_counts()

    assert counts.platform == "twitter"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is not None
    assert counts.following_count >= 0
