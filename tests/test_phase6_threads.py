"""Phase 6 Threads adapter and CLI flow tests."""

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
from sm_tracker.platforms.threads import ThreadsAdapter, create_threads_adapter


class _FakeThreadsUsers:
    def __init__(self, profile: object) -> None:
        self.profile = profile
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def get(self, *, user_id: str, fields: list[str] | None = None) -> object:
        selected_fields = tuple(fields or [])
        self.calls.append((user_id, selected_fields))
        return self.profile


class _FakeThreadsInsights:
    def __init__(self, followers_count: int) -> None:
        self.followers_count = followers_count
        self.calls: list[str] = []

    def get_user_insights(self, user_id: str) -> "_FakeThreadsInsights":
        self.calls.append(user_id)
        return self

    def get_metric(self, key: str) -> int:
        if key == "followers_count":
            return self.followers_count
        return 0


def _extract_profile_follower_count(profile: object) -> int:
    value = getattr(profile, "follower_count", None)
    if value is None and isinstance(profile, dict):
        value = profile.get("follower_count")
    if value is None:
        return 0
    return int(value)


class _FakeThreadsClient:
    def __init__(self, profile: object) -> None:
        self.users = _FakeThreadsUsers(profile=profile)
        self.insights = _FakeThreadsInsights(
            followers_count=_extract_profile_follower_count(profile),
        )
        self.closed = False

    def close(self) -> None:
        self.closed = True


def test_create_threads_adapter_requires_access_token() -> None:
    try:
        create_threads_adapter({"THREADS_USER_ID": "123"})
    except AdapterConfigError as exc:
        assert "missing THREADS_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing THREADS_ACCESS_TOKEN.")


def test_create_threads_adapter_requires_user_id() -> None:
    try:
        create_threads_adapter({"THREADS_ACCESS_TOKEN": "token"})
    except AdapterConfigError as exc:
        assert "missing THREADS_USER_ID" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing THREADS_USER_ID.")


def test_threads_adapter_fetch_counts(monkeypatch: MonkeyPatch) -> None:
    adapter = ThreadsAdapter(access_token="token", user_id="123")
    fake_client = _FakeThreadsClient(
        profile=SimpleNamespace(follower_count=312, following_count=91),
    )
    monkeypatch.setattr(
        ThreadsAdapter,
        "_build_client",
        lambda _self: fake_client,
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "threads"
    assert counts.follower_count == 312
    assert counts.following_count == 91
    assert fake_client.insights.calls == ["123"]
    assert fake_client.users.calls == [("123", ())]
    assert fake_client.closed is True


def test_track_and_show_threads_end_to_end(monkeypatch: MonkeyPatch, tmp_path: Path) -> None:
    _ = tmp_path
    runner = CliRunner()
    env = {
        "THREADS_ACCESS_TOKEN": "token",
        "THREADS_USER_ID": "123",
    }
    profile_sequence = iter(
        [
            {"follower_count": 500, "following_count": 100},
            {"follower_count": 507, "following_count": 96},
        ]
    )

    def _next_client(_self: ThreadsAdapter) -> _FakeThreadsClient:
        profile: dict[str, Any] = next(profile_sequence)
        return _FakeThreadsClient(profile=profile)

    monkeypatch.setattr(
        ThreadsAdapter,
        "_build_client",
        _next_client,
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

        first_track = runner.invoke(app, ["track", "-p", "threads"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "threads"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "threads"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "threads"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: threads" in first_track.stdout
    assert "Tracking snapshot for: threads" in second_track.stdout
    assert "threads" in show_result.stdout
    assert "Followers: 507 (+7)" in show_result.stdout
    assert "Following: 96 (-4)" in show_result.stdout
    assert "Date | Platform | Followers | Following" in history_result.stdout
    assert "threads" in history_result.stdout


def test_threads_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Threads credentials against the real API."""
    access_token = os.getenv("THREADS_ACCESS_TOKEN", "").strip()
    user_id = os.getenv("THREADS_USER_ID", "").strip()
    if not access_token or not user_id:
        pytest.skip("Set THREADS_ACCESS_TOKEN and THREADS_USER_ID to run live Threads test.")

    adapter = ThreadsAdapter(access_token=access_token, user_id=user_id)
    counts = adapter.fetch_counts()

    assert counts.platform == "threads"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is not None
    assert counts.following_count >= 0
