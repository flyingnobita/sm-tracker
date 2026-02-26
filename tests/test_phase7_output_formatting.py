"""Phase 7 output formatting and edge-case tests."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from typing import Any

from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import _format_delta, app
from sm_tracker.platforms.bluesky import BlueskyAdapter
from sm_tracker.platforms.twitter import TwitterAdapter


class _FakeBlueskyClient:
    def __init__(self, profile: object) -> None:
        self.profile = profile

    def login(self, identifier: str, password: str) -> None:
        _ = (identifier, password)

    def get_profile(self, *, actor: str) -> object:
        _ = actor
        return self.profile


class _FakeTwitterClient:
    def __init__(self, metrics: dict[str, Any]) -> None:
        self.metrics = metrics

    def get_user(self, *, username: str, user_fields: list[str]) -> object:
        _ = (username, user_fields)
        return SimpleNamespace(
            data=SimpleNamespace(public_metrics=self.metrics),
        )


def _write_test_config(path: Path) -> None:
    path.write_text(
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


def test_format_delta_rules() -> None:
    assert _format_delta(current=132, previous=None) == "N/A"
    assert _format_delta(current=None, previous=122) == "N/A"
    assert _format_delta(current=132, previous=122) == "+10"
    assert _format_delta(current=121, previous=122) == "-1"
    assert _format_delta(current=132, previous=132) == "0"


def test_show_first_snapshot_displays_na_delta(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "TWITTER_BEARER_TOKEN": "token",
        "TWITTER_HANDLE": "alice",
    }
    monkeypatch.setattr(
        TwitterAdapter,
        "_build_client",
        lambda _self: _FakeTwitterClient(
            metrics={"followers_count": 200, "following_count": 50},
        ),
    )

    with runner.isolated_filesystem():
        _write_test_config(Path("config.toml"))
        track_result = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "twitter"], env=env)

    assert track_result.exit_code == 0
    assert show_result.exit_code == 0
    assert "Followers: 200 (N/A)" in show_result.stdout
    assert "Following: 50 (N/A)" in show_result.stdout


def test_show_following_na_for_platforms_without_following(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "BLUESKY_HANDLE": "alice.bsky.social",
    }
    monkeypatch.setattr(
        BlueskyAdapter,
        "_build_client",
        lambda _self: _FakeBlueskyClient(
            profile=SimpleNamespace(followers_count=321),
        ),
    )

    with runner.isolated_filesystem():
        _write_test_config(Path("config.toml"))
        track_result = runner.invoke(app, ["track", "-p", "bluesky"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "bluesky"], env=env)

    assert track_result.exit_code == 0
    assert show_result.exit_code == 0
    assert "Followers: 321 (N/A)" in show_result.stdout
    assert "Following: N/A" in show_result.stdout


def test_history_table_includes_delta_column(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "TWITTER_BEARER_TOKEN": "token",
        "TWITTER_HANDLE": "alice",
    }
    metrics_sequence = iter(
        [
            {"followers_count": 100, "following_count": 25},
            {"followers_count": 104, "following_count": 25},
            {"followers_count": 104, "following_count": 25},
        ]
    )
    monkeypatch.setattr(
        TwitterAdapter,
        "_build_client",
        lambda _self: _FakeTwitterClient(next(metrics_sequence)),
    )

    with runner.isolated_filesystem():
        _write_test_config(Path("config.toml"))
        first_track = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        third_track = runner.invoke(app, ["track", "-p", "twitter"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "twitter"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert third_track.exit_code == 0
    assert history_result.exit_code == 0
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout
    assert "twitter | 104 | 25 | 0" in history_result.stdout
    assert "twitter | 100 | 25 | N/A" in history_result.stdout
    assert "twitter | 104 | 25 | +4" in history_result.stdout


def test_track_warns_and_keeps_partial_snapshot_on_fetch_error(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "TWITTER_BEARER_TOKEN": "token",
        "TWITTER_HANDLE": "alice",
        "BLUESKY_HANDLE": "alice.bsky.social",
    }
    monkeypatch.setattr(
        TwitterAdapter,
        "fetch_counts",
        lambda _self: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    monkeypatch.setattr(
        BlueskyAdapter,
        "_build_client",
        lambda _self: _FakeBlueskyClient(
            profile=SimpleNamespace(followers_count=55, follows_count=11),
        ),
    )

    with runner.isolated_filesystem():
        _write_test_config(Path("config.toml"))
        track_result = runner.invoke(app, ["track", "-p", "twitter", "-p", "bluesky"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "bluesky"], env=env)

    assert track_result.exit_code == 0
    assert show_result.exit_code == 0
    assert "Skipping twitter: fetch failed (boom)" in track_result.stdout
    assert "Tracking snapshot for: bluesky" in track_result.stdout
    assert "Followers: 55 (N/A)" in show_result.stdout
