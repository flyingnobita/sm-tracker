"""Tests for the YouTube platform adapter."""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import Mock, patch

import pytest

from sm_tracker.platforms import AdapterConfigError, PlatformCounts
from sm_tracker.platforms.youtube import YouTubeAdapter, create_youtube_adapter


def test_create_youtube_adapter_with_handle() -> None:
    env = {
        "YOUTUBE_API_KEY": "test_key",
        "YOUTUBE_HANDLE": "@test_channel",
    }
    adapter = create_youtube_adapter(env)
    assert adapter.api_key == "test_key"
    assert adapter.handle == "@test_channel"
    assert adapter.channel_id is None
    assert adapter.name == "youtube"


def test_create_youtube_adapter_with_channel_id() -> None:
    env = {
        "YOUTUBE_API_KEY": "test_key",
        "YOUTUBE_CHANNEL_ID": "UC_test_id",
    }
    adapter = create_youtube_adapter(env)
    assert adapter.api_key == "test_key"
    assert adapter.channel_id == "UC_test_id"
    assert adapter.handle is None


def test_create_youtube_adapter_missing_api_key() -> None:
    env = {
        "YOUTUBE_HANDLE": "@test_channel",
    }
    with pytest.raises(AdapterConfigError, match="missing YOUTUBE_API_KEY"):
        create_youtube_adapter(env)


def test_create_youtube_adapter_missing_handle_and_id() -> None:
    env = {
        "YOUTUBE_API_KEY": "test_key",
    }
    with pytest.raises(AdapterConfigError, match="missing YOUTUBE_CHANNEL_ID or YOUTUBE_HANDLE"):
        create_youtube_adapter(env)


def test_youtube_adapter_post_init_validation() -> None:
    with pytest.raises(ValueError, match="requires either a handle or a channel_id"):
        YouTubeAdapter(api_key="test_key")


def _mock_response(payload: dict[str, Any]) -> Mock:
    mock_resp = Mock()
    mock_resp.read.return_value = json.dumps(payload).encode("utf-8")
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=None)
    return mock_resp


@patch("sm_tracker.platforms.youtube.urlopen")
def test_fetch_counts_success_with_handle(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = _mock_response(
        {"items": [{"statistics": {"subscriberCount": "12345"}}]}
    )

    adapter = YouTubeAdapter(api_key="test_key", handle="@test")
    counts = adapter.fetch_counts()

    assert counts == PlatformCounts(
        platform="youtube",
        follower_count=12345,
        following_count=None,
    )

    # Verify the URL construction
    request = mock_urlopen.call_args[0][0]
    assert "forHandle=%40test" in request.full_url
    assert "key=test_key" in request.full_url


@patch("sm_tracker.platforms.youtube.urlopen")
def test_fetch_counts_success_with_channel_id(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = _mock_response(
        {"items": [{"statistics": {"subscriberCount": "9876"}}]}
    )

    adapter = YouTubeAdapter(api_key="test_key", channel_id="UC123")
    counts = adapter.fetch_counts()

    assert counts == PlatformCounts(
        platform="youtube",
        follower_count=9876,
        following_count=None,
    )

    # Verify the URL construction
    request = mock_urlopen.call_args[0][0]
    assert "id=UC123" in request.full_url
    assert "key=test_key" in request.full_url


@patch("sm_tracker.platforms.youtube.urlopen")
def test_fetch_counts_empty_items(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = _mock_response({"items": []})

    adapter = YouTubeAdapter(api_key="test_key", handle="@test")
    counts = adapter.fetch_counts()

    assert counts == PlatformCounts(
        platform="youtube",
        follower_count=None,
        following_count=None,
    )


@patch("sm_tracker.platforms.youtube.urlopen")
def test_fetch_counts_missing_statistics(mock_urlopen: Mock) -> None:
    mock_urlopen.return_value = _mock_response({"items": [{"id": "UC123"}]})

    adapter = YouTubeAdapter(api_key="test_key", handle="@test")
    counts = adapter.fetch_counts()

    assert counts == PlatformCounts(
        platform="youtube",
        follower_count=None,
        following_count=None,
    )


@patch("sm_tracker.platforms.youtube.urlopen")
def test_fetch_counts_invalid_json(mock_urlopen: Mock) -> None:
    mock_resp = Mock()
    mock_resp.read.return_value = b"invalid json"
    mock_resp.__enter__ = Mock(return_value=mock_resp)
    mock_resp.__exit__ = Mock(return_value=None)
    mock_urlopen.return_value = mock_resp

    adapter = YouTubeAdapter(api_key="test_key", handle="@test")

    # json.loads will raise json.JSONDecodeError, which is unhandled
    # per constraints to let standard API failures bubble up unless we try-except it.
    # The adapter doesn't wrap json.loads in try/except in the current impl.
    with pytest.raises(json.JSONDecodeError):
        adapter.fetch_counts()
