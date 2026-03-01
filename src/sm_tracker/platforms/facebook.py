"""Facebook platform adapter."""

from __future__ import annotations

import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote
from urllib.request import Request, urlopen

from sm_tracker.platforms import AdapterConfigError, BaseAdapter, PlatformCounts
from sm_tracker.platforms.utils import extract_int

GRAPH_API_VERSION = "v19.0"


@dataclass(frozen=True)
class FacebookAdapter(BaseAdapter):
    """Fetch Facebook follower counts for one target ID (Page, Group, or User)."""

    target_id: str | None = None
    access_token: str | None = field(default=None, repr=False)
    user_token: str | None = field(default=None, repr=False)

    @property
    def name(self) -> str:
        return "facebook"

    def _build_request(self, target_id: str, access_token: str) -> Request:
        target_encoded = quote(target_id, safe="")
        # We request multiple fields to support polymorphic IDs (Page, User)
        # Note: member_count for groups causes #100 errors on Pages.
        url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/{target_encoded}?fields=followers_count,fan_count"
        return Request(
            url,
            headers={
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "curl/8.7.1",
            },
        )

    def _request_graph_payload(self, target_id: str, access_token: str) -> Mapping[str, Any]:
        request = self._build_request(target_id, access_token)
        with urlopen(request, timeout=30) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, Mapping):
            return payload
        return {}  # pragma: no cover

    def _resolve_credentials(self) -> tuple[str, str]:
        target_id = self.target_id
        access_token = self.access_token

        if access_token and not target_id:
            url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me?fields=id"
            request = Request(
                url,
                headers={
                    "Authorization": f"Bearer {access_token}",
                    "User-Agent": "curl/8.7.1",
                },
            )
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

        elif self.user_token and target_id and not access_token:
            access_token = _fetch_page_token(self.user_token, target_id)

        if not target_id or not access_token:
            raise AdapterConfigError(
                "Skipping facebook: valid target ID and access token could not be resolved."
            )

        return target_id, access_token

    def fetch_counts(self) -> PlatformCounts:
        target_id, access_token = self._resolve_credentials()
        payload = self._request_graph_payload(target_id, access_token)

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

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> FacebookAdapter:
        """Create a Facebook adapter from env vars.

        If FACEBOOK_PAGE_ACCESS_TOKEN is provided, it is used directly.
        Otherwise, if FACEBOOK_ACCESS_TOKEN (User Token) and FACEBOOK_ID are provided,
        it automatically exchanges them for a Page Token in fetch_counts.
        """
        page_token = env.get("FACEBOOK_PAGE_ACCESS_TOKEN", "").strip()
        target_id = env.get("FACEBOOK_ID", "").strip()
        user_token = env.get("FACEBOOK_ACCESS_TOKEN", "").strip()

        if not page_token and not user_token:
            raise AdapterConfigError(
                "Skipping facebook: missing FACEBOOK_PAGE_ACCESS_TOKEN or FACEBOOK_ACCESS_TOKEN."
            )

        if user_token and not page_token and not target_id:
            raise AdapterConfigError(
                "Skipping facebook: FACEBOOK_ID is required when using FACEBOOK_ACCESS_TOKEN."
            )

        return cls(
            target_id=target_id if target_id else None,
            access_token=page_token if page_token else None,
            user_token=user_token if user_token else None,
        )


def _fetch_page_token(user_token: str, target_id: str) -> str:
    """Exchange a User Access Token for a specific Page Access Token."""
    url = f"https://graph.facebook.com/{GRAPH_API_VERSION}/me/accounts?limit=100"
    request = Request(
        url,
        headers={
            "Authorization": f"Bearer {user_token}",
            "User-Agent": "curl/8.7.1",
        },
    )

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
