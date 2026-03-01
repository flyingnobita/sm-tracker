"""Tests for the Instagram adapter."""

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from sm_tracker.platforms import AdapterConfigError
from sm_tracker.platforms.instagram import InstagramAdapter, create_instagram_adapter


def test_create_instagram_adapter_success() -> None:
    env = {
        "INSTAGRAM_ACCOUNT_ID": "12345",
        "LONG_LIVED_USER_TOKEN": "abcde",
        "INSTAGRAM_USERNAME": "testuser",
    }
    adapter = create_instagram_adapter(env)
    assert adapter.account_id == "12345"
    assert adapter.access_token == "abcde"
    assert adapter.username == "testuser"
    assert adapter.name == "instagram"


def test_create_instagram_adapter_no_username() -> None:
    env = {
        "INSTAGRAM_ACCOUNT_ID": "12345",
        "LONG_LIVED_USER_TOKEN": "abcde",
    }
    adapter = create_instagram_adapter(env)
    assert adapter.username is None


def test_create_instagram_adapter_missing_config() -> None:
    env: dict[str, str] = {"INSTAGRAM_ACCOUNT_ID": "123"}
    with pytest.raises(
        AdapterConfigError,
        match="missing INSTAGRAM_ACCOUNT_ID or LONG_LIVED_USER_TOKEN",
    ):
        create_instagram_adapter(env)

    env = {"LONG_LIVED_USER_TOKEN": "abc"}
    with pytest.raises(
        AdapterConfigError,
        match="missing INSTAGRAM_ACCOUNT_ID or LONG_LIVED_USER_TOKEN",
    ):
        create_instagram_adapter(env)


@patch("urllib.request.urlopen")
def test_fetch_counts_success_own_account(mock_urlopen: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "followers_count": 1500,
            "follows_count": 200,
        }
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    adapter = InstagramAdapter(account_id="123", access_token="abc")
    counts = adapter.fetch_counts()

    assert mock_urlopen.called
    req = mock_urlopen.call_args[0][0]
    assert (
        req.full_url
        == "https://graph.facebook.com/v19.0/123?fields=followers_count,follows_count&access_token=abc"
    )

    assert counts.platform == "instagram"
    assert counts.follower_count == 1500
    assert counts.following_count == 200


@patch("urllib.request.urlopen")
def test_fetch_counts_success_with_username(mock_urlopen: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(
        {
            "business_discovery": {
                "followers_count": 800,
                "follows_count": 100,
            }
        }
    ).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    adapter = InstagramAdapter(account_id="123", access_token="abc", username="target")
    counts = adapter.fetch_counts()

    assert mock_urlopen.called
    req = mock_urlopen.call_args[0][0]
    expected_url = (
        "https://graph.facebook.com/v19.0/123?"
        "fields=business_discovery.username(target){followers_count,follows_count}&access_token=abc"
    )
    assert req.full_url == expected_url

    assert counts.follower_count == 800
    assert counts.following_count == 100


@patch("urllib.request.urlopen")
def test_fetch_counts_http_error(mock_urlopen: MagicMock) -> None:
    error_fp = BytesIO(b'{"error": {"message": "Invalid token"}}')
    mock_urlopen.side_effect = urllib.error.HTTPError(
        url="http://test",
        code=400,
        msg="Bad Request",
        hdrs=MagicMock(),
        fp=error_fp,
    )

    adapter = InstagramAdapter(account_id="123", access_token="abc")

    with pytest.raises(RuntimeError, match=r"Instagram API Error \(400\): .*Invalid token.*"):
        adapter.fetch_counts()


@patch("urllib.request.urlopen")
def test_fetch_counts_missing_business_discovery(mock_urlopen: MagicMock) -> None:
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps({"id": "123"}).encode("utf-8")
    mock_urlopen.return_value.__enter__.return_value = mock_response

    adapter = InstagramAdapter(account_id="123", access_token="abc", username="target")

    with pytest.raises(RuntimeError, match="Missing business_discovery data for 'target'"):
        adapter.fetch_counts()
