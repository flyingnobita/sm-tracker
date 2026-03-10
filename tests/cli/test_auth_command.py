"""Auth command helper tests."""

from __future__ import annotations

from urllib.parse import parse_qs, urlparse

from sm_tracker.cli.auth import _build_meta_accounts_request, _build_meta_token_exchange_request


def test_build_meta_token_exchange_request_uses_post_body() -> None:
    request = _build_meta_token_exchange_request(
        app_id="app-id",
        app_secret="app-secret",
        short_token="short-token",
    )

    assert request.full_url == "https://graph.facebook.com/v19.0/oauth/access_token"
    assert request.get_method() == "POST"
    assert request.headers["Content-type"] == "application/x-www-form-urlencoded"
    assert request.data is not None

    params = parse_qs(request.data.decode("utf-8"))
    assert params == {
        "grant_type": ["fb_exchange_token"],
        "client_id": ["app-id"],
        "client_secret": ["app-secret"],
        "fb_exchange_token": ["short-token"],
    }


def test_build_meta_accounts_request_uses_authorization_header() -> None:
    request = _build_meta_accounts_request("long-user-token")

    parsed = urlparse(request.full_url)
    assert request.full_url == "https://graph.facebook.com/v19.0/me/accounts"
    assert parsed.query == ""
    assert request.get_header("Authorization") == "Bearer long-user-token"
