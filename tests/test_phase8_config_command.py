"""Phase 8 config command tests."""

from __future__ import annotations

from pathlib import Path

from typer.testing import CliRunner

from sm_tracker.cli import app


def _guided_input_for_full_setup() -> str:
    return (
        "\n".join(
            [
                "twitter-ck",
                "twitter-cs",
                "twitter-at",
                "twitter-ats",
                "alice",
                "alice.bsky.social",
                "",
                "warpcast-key",
                "alice-fc",
                "mastodon-token",
                "mastodon.social",
                "",
                "",
                "https://localhost/callback",
                "threads-token",
                "12345",
                "",
                "insta-id",
                "insta-token",
                "fb-id",
                "fb-token",
                "",
                "",
                "",
                "",
                "youtube-key",
                "UC12345",
                "",
                "dev",
                "./data-dev.db",
                "./logs-dev",
                "7",
                "DEBUG",
            ]
        )
        + "\n"
    )


def _guided_input_with_empty_required_values() -> str:
    return "\n" * 40


def test_config_command_guided_flow_creates_env_and_config() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["config"], input=_guided_input_for_full_setup())

        env_contents = Path(".env").read_text(encoding="utf-8")
        config_contents = Path("config.toml").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "Guided setup for .env and config.toml" in result.stdout
    assert "Validation passed. Configuration looks good." in result.stdout
    assert "TWITTER_CONSUMER_KEY=twitter-ck" in env_contents
    assert "BLUESKY_HANDLE=alice.bsky.social" in env_contents
    assert "THREADS_ACCESS_TOKEN=threads-token" in env_contents
    assert "INSTAGRAM_ACCOUNT_ID=insta-id" in env_contents
    assert "FACEBOOK_ID=fb-id" in env_contents
    assert "YOUTUBE_API_KEY=youtube-key" in env_contents
    assert "YOUTUBE_CHANNEL_ID=UC12345" in env_contents
    assert 'profile = "dev"' in config_contents
    assert 'db = "./data-dev.db"' in config_contents
    assert 'logs = "./logs-dev"' in config_contents
    assert "retention_days = 7" in config_contents
    assert 'level = "DEBUG"' in config_contents


def test_config_command_shows_validation_warnings_for_missing_required_env_values() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        result = runner.invoke(app, ["config"], input=_guided_input_with_empty_required_values())
        env_contents = Path(".env").read_text(encoding="utf-8")

    assert result.exit_code == 0
    assert "Validation warnings:" in result.stdout
    assert (
        "twitter: missing TWITTER_CONSUMER_KEY, TWITTER_CONSUMER_SECRET, TWITTER_ACCESS_TOKEN, TWITTER_ACCESS_TOKEN_SECRET, TWITTER_HANDLE"  # noqa: E501
        in result.stdout
    )
    assert "bluesky: missing BLUESKY_HANDLE" in result.stdout
    assert "farcaster: missing FARCASTER_API_KEY, FARCASTER_USERNAME" in result.stdout
    assert "mastodon: missing MASTODON_ACCESS_TOKEN, MASTODON_INSTANCE" in result.stdout
    assert "threads: missing THREADS_ACCESS_TOKEN, THREADS_USER_ID" in result.stdout
    assert "instagram: missing INSTAGRAM_ACCOUNT_ID, LONG_LIVED_USER_TOKEN" in result.stdout
    assert "facebook: missing FACEBOOK_ACCESS_TOKEN, FACEBOOK_ID" in result.stdout
    assert "youtube: missing YOUTUBE_API_KEY, YOUTUBE_CHANNEL_ID or YOUTUBE_HANDLE" in result.stdout
    assert "TWITTER_CONSUMER_KEY=" not in env_contents


def test_config_command_warns_when_existing_config_toml_is_invalid() -> None:
    runner = CliRunner()
    with runner.isolated_filesystem():
        Path("config.toml").write_text(
            """
profile = "dev"

[paths.dev]
db = "./dev.db"
logs = "./logs-dev"

[logging.dev]
retention_days = 0
level = "INFO"
""".strip()
            + "\n",
            encoding="utf-8",
        )
        result = runner.invoke(app, ["config"], input=_guided_input_for_full_setup())

    assert result.exit_code == 0
    assert "Found existing configuration warnings:" in result.stdout
    assert "config.toml error:" in result.stdout
