"""Phase 6 Mastodon adapter and CLI flow tests."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import pytest
from pytest import MonkeyPatch
from typer.testing import CliRunner

from sm_tracker.cli import app
from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.mastodon import MastodonAdapter, create_mastodon_adapter


class _FakeMastodonClient:
    def __init__(self, account: dict[str, Any]) -> None:
        self.account = account

    def account_verify_credentials(self) -> dict[str, Any]:
        return self.account


def test_create_mastodon_adapter_requires_access_token() -> None:
    try:
        create_mastodon_adapter({"MASTODON_INSTANCE": "mastodon.social"})
    except AdapterConfigError as exc:
        assert "missing MASTODON_ACCESS_TOKEN" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing MASTODON_ACCESS_TOKEN.")


def test_create_mastodon_adapter_requires_instance() -> None:
    try:
        create_mastodon_adapter({"MASTODON_ACCESS_TOKEN": "token"})
    except AdapterConfigError as exc:
        assert "missing MASTODON_INSTANCE" in str(exc)
    else:
        raise AssertionError("Expected AdapterConfigError for missing MASTODON_INSTANCE.")


def test_mastodon_adapter_fetch_counts(monkeypatch: MonkeyPatch) -> None:
    adapter = MastodonAdapter(
        access_token="token",
        instance="mastodon.social",
    )
    fake_client = _FakeMastodonClient(
        account={"followers_count": 78, "following_count": 41},
    )
    monkeypatch.setattr(
        MastodonAdapter,
        "_build_client",
        lambda _self: fake_client,
    )

    counts = adapter.fetch_counts()

    assert counts.platform == "mastodon"
    assert counts.follower_count == 78
    assert counts.following_count == 41


def test_track_and_show_mastodon_end_to_end(monkeypatch: MonkeyPatch) -> None:
    runner = CliRunner()
    env = {
        "MASTODON_ACCESS_TOKEN": "token",
        "MASTODON_INSTANCE": "mastodon.social",
    }
    account_sequence = iter(
        [
            {"followers_count": 99, "following_count": 30},
            {"followers_count": 102, "following_count": 28},
        ]
    )

    monkeypatch.setattr(
        MastodonAdapter,
        "_build_client",
        lambda _self: _FakeMastodonClient(next(account_sequence)),
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

        first_track = runner.invoke(app, ["track", "-p", "mastodon"], env=env)
        second_track = runner.invoke(app, ["track", "-p", "mastodon"], env=env)
        show_result = runner.invoke(app, ["show", "-p", "mastodon"], env=env)
        history_result = runner.invoke(app, ["history", "-p", "mastodon"], env=env)

    assert first_track.exit_code == 0
    assert second_track.exit_code == 0
    assert show_result.exit_code == 0
    assert history_result.exit_code == 0
    assert "Tracking snapshot for: mastodon" in first_track.stdout
    assert "Tracking snapshot for: mastodon" in second_track.stdout
    assert "mastodon" in show_result.stdout
    assert "Followers: 102 (+3)" in show_result.stdout
    assert "Following: 28 (-2)" in show_result.stdout
    assert "Date | Platform | Followers | Following | Delta" in history_result.stdout
    assert "mastodon" in history_result.stdout


def test_mastodon_live_credentials_fetch_counts() -> None:
    """Opt-in live test that validates Mastodon credentials against the real API."""
    access_token = os.getenv("MASTODON_ACCESS_TOKEN", "").strip()
    instance = os.getenv("MASTODON_INSTANCE", "").strip()
    if not access_token or not instance:
        pytest.skip("Set MASTODON_ACCESS_TOKEN and MASTODON_INSTANCE to run live Mastodon test.")

    adapter = MastodonAdapter(access_token=access_token, instance=instance)
    counts = adapter.fetch_counts()

    assert counts.platform == "mastodon"
    assert counts.follower_count is not None
    assert counts.follower_count >= 0
    assert counts.following_count is not None
    assert counts.following_count >= 0
