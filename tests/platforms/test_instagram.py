"""Tests for the Instagram adapter."""

from unittest.mock import MagicMock, patch

import pytest

from sm_tracker.platforms import AdapterConfigError, PlatformCounts
from sm_tracker.platforms.instagram import InstagramAdapter, create_instagram_adapter


def test_create_instagram_adapter_success() -> None:
    env = {"INSTAGRAM_USERNAME": "testuser"}
    adapter = create_instagram_adapter(env)
    assert adapter.username == "testuser"
    assert adapter.name == "instagram"


def test_create_instagram_adapter_missing_username() -> None:
    env: dict[str, str] = {}
    with pytest.raises(AdapterConfigError, match="missing INSTAGRAM_USERNAME"):
        create_instagram_adapter(env)


def test_create_instagram_adapter_empty_username() -> None:
    env = {"INSTAGRAM_USERNAME": "   "}
    with pytest.raises(AdapterConfigError, match="missing INSTAGRAM_USERNAME"):
        create_instagram_adapter(env)


@patch("sm_tracker.platforms.instagram.instaloader.Instaloader")
@patch("sm_tracker.platforms.instagram.instaloader.Profile")
def test_fetch_counts_success(
    mock_profile_class: MagicMock, mock_instaloader_class: MagicMock
) -> None:
    # Mock Instaloader instance
    mock_instaloader_instance = MagicMock()
    mock_instaloader_class.return_value = mock_instaloader_instance

    # Mock Profile class behavior
    mock_profile_instance = MagicMock()
    mock_profile_instance.followers = 1500
    mock_profile_instance.followees = 200
    mock_profile_class.from_username.return_value = mock_profile_instance

    adapter = InstagramAdapter(username="testuser")
    counts = adapter.fetch_counts()

    assert mock_instaloader_class.called
    mock_profile_class.from_username.assert_called_once_with(
        mock_instaloader_instance.context, "testuser"
    )

    assert isinstance(counts, PlatformCounts)
    assert counts.platform == "instagram"
    assert counts.follower_count == 1500
    assert counts.following_count == 200


@patch("sm_tracker.platforms.instagram.instaloader.Instaloader")
@patch("sm_tracker.platforms.instagram.instaloader.Profile")
def test_fetch_counts_failure(
    mock_profile_class: MagicMock, mock_instaloader_class: MagicMock
) -> None:
    mock_instaloader_instance = MagicMock()
    mock_instaloader_class.return_value = mock_instaloader_instance

    mock_profile_class.from_username.side_effect = Exception("Profile not found")

    adapter = InstagramAdapter(username="baduser")

    with pytest.raises(RuntimeError, match="Failed to fetch profile 'baduser': Profile not found"):
        adapter.fetch_counts()
