"""Facebook platform adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from sm_tracker.platforms import AdapterConfigError, PlatformCounts
from sm_tracker.platforms.utils import extract_int


@dataclass(frozen=True)
class FacebookAdapter:
    """Fetch Facebook follower counts for one target ID (Page, Group, or User)."""

    target_id: str
    access_token: str
    name: str = "facebook"

    def _build_request(self) -> Request:
        target_encoded = quote(self.target_id, safe="")
        # We request multiple fields to support polymorphic IDs (Page, User)
        # Note: member_count for groups causes #100 errors on Pages.
        url = f"https://graph.facebook.com/v19.0/{target_encoded}?fields=followers_count,fan_count"
        return Request(
            url,
            headers={
                "Authorization": f"Bearer {self.access_token}",
                "User-Agent": "curl/8.7.1",
            },
        )

    def _request_graph_payload(self) -> Mapping[str, Any]:
        request = self._build_request()
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, Mapping):
            return payload
        return {}  # pragma: no cover

    def fetch_counts(self) -> PlatformCounts:
        payload = self._request_graph_payload()

        # Facebook returns likes as `fan_count` and actual followers as `followers_count` on Pages.
        # Groups return members as `member_count`.
        # We prioritize actual followers, then fallback to fan count, then member count.
        follower_count = extract_int(payload, "followers_count", "followersCount")
        if follower_count is None:
            follower_count = extract_int(payload, "fan_count", "fanCount")
        if follower_count is None:
            follower_count = extract_int(payload, "member_count", "memberCount")

        return PlatformCounts(
            platform=self.name,
            follower_count=follower_count,
            following_count=None,  # Facebook API rarely exposes "following"
        )


def _fetch_page_token(user_token: str, target_id: str) -> str:
    """Exchange a User Access Token for a specific Page Access Token."""
    # Build URL to fetch accounts (pages) managed by this user
    # We ask for a high limit to ensure we find the page if they manage many
    url = f"https://graph.facebook.com/v19.0/me/accounts?limit=100&access_token={quote(user_token)}"
    request = Request(url, headers={"User-Agent": "curl/8.7.1"})

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except Exception as e:
        raise AdapterConfigError(f"Failed to fetch Facebook Page token: {e}") from e

    for page in payload.get("data", []):
        if not isinstance(page, Mapping):
            continue
        if page.get("id") == target_id and "access_token" in page:
            return str(page["access_token"])

    raise AdapterConfigError(
        f"Could not find Page Access Token for ID {target_id}. "
        "Ensure the User Token has administrative access to this page."
    )


def create_facebook_adapter(env: Mapping[str, str]) -> FacebookAdapter:
    """Create a Facebook adapter from env vars.

    If FACEBOOK_PAGE_ACCESS_TOKEN is provided, it is used directly.
    Otherwise, if FACEBOOK_ACCESS_TOKEN (User Token) and FACEBOOK_ID are provided,
    it automatically exchanges them for a Page Token.
    """
    page_token = env.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
    target_id = env.get("FACEBOOK_ID", "").strip()

    # Fast path: user directly provided the specific page token
    if page_token:
        # If no target_id was given, we can ask the API who this token belongs to
        if not target_id:
            url = f"https://graph.facebook.com/v19.0/me?fields=id&access_token={quote(page_token)}"
            request = Request(url, headers={"User-Agent": "curl/8.7.1"})
            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.loads(response.read().decode("utf-8"))
                    target_id = payload.get("id", "")
            except Exception as e:
                raise AdapterConfigError(
                    f"Failed to identify Page ID from FACEBOOK_PAGE_ACCESS_TOKEN: {e}"
                ) from e

            if not target_id:
                raise AdapterConfigError(
                    "FACEBOOK_PAGE_ACCESS_TOKEN is invalid or does not belong to a valid Page."
                )

        return FacebookAdapter(target_id=target_id, access_token=page_token)

    # Fallback path: user provided a generic User Token and a specific target ID
    user_token = env.get("FACEBOOK_ACCESS_TOKEN", "").strip()
    if not user_token:
        raise AdapterConfigError(
            "Skipping facebook: missing FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN."
        )

    if not target_id:
        raise AdapterConfigError(
            "Skipping facebook: FACEBOOK_ID is required when using FACEBOOK_ACCESS_TOKEN."
        )

    # Exchange the user token for the page token
    resolved_page_token = _fetch_page_token(user_token, target_id)

    return FacebookAdapter(target_id=target_id, access_token=resolved_page_token)
