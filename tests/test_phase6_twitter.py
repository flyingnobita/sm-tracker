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

_FAKE_ENV = {
    "TWITTER_CONSUMER_KEY": "ck",
    "TWITTER_CONSUMER_SECRET": "cs",
    "TWITTER_ACCESS_TOKEN": "at",
    "TWITTER_ACCESS_TOKEN_SECRET": "ats",
    "TWITTER_HANDLE": "alice",
}


class _FakeTwitterClient:
    def __init__(self, metrics: dict[str, Any]) -> None:
        self.metrics = metrics
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def get_user(self, *, username: str, user_fields: list[str], user_auth: bool = False) -> object:
        self.calls.append((username, tuple(user_fields)))
        return SimpleNamespace(
            data=SimpleNamespace(public_metrics=self.metrics),
        )


def test_create_twitter_adapter_requires_consumer_key() -> None:
    env = {k: v for k, v in _FAKE_ENV.items() if k != "TWITTER_CONSUMER_KEY"}
    try:
        create_twitter_adapter(env)
    except AdapterConfigError as exc:
        assert "missing TWITTER_CONSUMER_KEY" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_CONSUMER_KEY.")


def test_create_twitter_adapter_requires_consumer_secret() -> None:
    env = {k: v for k, v in _FAKE_ENV.items() if k != "TWITTER_CONSUMER_SECRET"}
    try:
        create_twitter_adapter(env)
    except AdapterConfigError as exc:
        assert "missing TWITTER_CONSUMER_SECRET" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_CONSUMER_SECRET.")


def test_create_twitter_adapter_requires_access_token() -> None:
    env = {k: v for k, v in _FAKE_ENV.items() if k != "TWITTER_ACCESS_TOKEN"}
    try:
        create_twitter_adapter(env)
    except AdapterConfigError as exc:
        assert "missing TWITTER_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_ACCESS_TOKEN.")


def test_create_twitter_adapter_requires_access_token_secret() -> None:
    env = {k: v for k, v in _FAKE_ENV.items() if k != "TWITTER_ACCESS_TOKEN_SECRET"}
    try:
        create_twitter_adapter(env)
    except AdapterConfigError as exc:
        assert "missing TWITTER_ACCESS_TOKEN_SECRET" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_ACCESS_TOKEN_SECRET.")


def test_create_twitter_adapter_requires_handle() -> None:
    env = {k: v for k, v in _FAKE_ENV.items() if k != "TWITTER_HANDLE"}
    try:
        create_twitter_adapter(env)
    except AdapterConfigError as exc:
        assert "missing TWITTER_HANDLE" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing TWITTER_HANDLE.")


def test_twitter_adapter_fetch_counts(monkeypatch: MonkeyPatch) -> None:
    adapter = TwitterAdapter(
        handle="alice",
        consumer_key="ck",
        consumer_secret="cs",
        access_token="at",
        access_token_secret="ats",
    )
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

        first_track = runner.invoke(app, ["track", "-p", "twitter"], env=_FAKE_ENV)
        second_track = runner.invoke(app, ["track", "-p", "twitter"], env=_FAKE_ENV)
        show_result = runner.invoke(app, ["show", "-p", "twitter"], env=_FAKE_ENV)
        history_result = runner.invoke(app, ["history", "-p", "twitter"], env=_FAKE_ENV)

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
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY", "").strip()
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET", "").strip()
    access_token = os.getenv("TWITTER_ACCESS_TOKEN", "").strip()
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET", "").strip()
    handle = os.getenv("TWITTER_HANDLE", "").strip()
    if not all([consumer_key, consumer_secret, access_token, access_token_secret, handle]):
        pytest.skip(
            "Set TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, "
            "TWITTER_ACCESS_TOKEN_SECRET, and TWITTER_HANDLE to run live Twitter test."
        )

    adapter = TwitterAdapter(
        handle=handle,
        consumer_key=consumer_key,
        consumer_secret=consumer_secret,
        access_token=access_token,
        access_token_secret=access_token_secret,
    )
    counts = adapter.fetch_counts()

    assert counts.platform == "twitter"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is not None
    assert counts.following_count >= 0
