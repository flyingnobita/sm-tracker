# Facebook Tracker Spec

Date: 2026-02-27
Status: Accepted

## Context

The `sm-tracker` CLI tool currenly supports tracking following/followers for Twitter, Bluesky, Farcaster, Mastodon, and Threads. Issue #4 requests adding support for Facebook tracking.

Facebook offers the Graph API, which requires authentication to fetch user metrics.

## Details

### Tech Stack Additions

- Use Python's built-in `urllib.request` to interface with the Facebook Graph API. This matches the approach used by the Farcaster adapter and avoids introducing new third-party dependencies like `requests` or `httpx`.

### Config & Credentials

`.env` modifications:

- `FACEBOOK_ACCESS_TOKEN` (Required): A long-lived Access Token with appropriate permissions (e.g., `pages_read_engagement` for Pages, `groups_access_member_info` for Groups, or user scopes).
- `FACEBOOK_ID` (Required): The tracking ID for the target. This can be a Facebook Page ID, Group ID, or User Profile ID.
- `FACEBOOK_APP_ID` (Optional, for auth command later)
- `FACEBOOK_APP_SECRET` (Optional, for auth command later)

`pyproject.toml` modifications:

- None. We will use `urllib.request`.

### Account Identifier

| Platform | Identifier | Example      |
| -------- | ---------- | ------------ |
| Facebook | Target ID  | `1234567890` |

### Platform Implementation

Create `src/sm_tracker/platforms/facebook.py`:

```python
@dataclass(frozen=True)
class FacebookAdapter:
    """Fetch Facebook follower/following counts."""
    target_id: str
    access_token: str
    name: str = "facebook"

    def fetch_counts(self) -> PlatformCounts:
        # Implement Graph API call to fetch followers/following
        pass

def create_facebook_adapter(env: Mapping[str, str]) -> FacebookAdapter:
    # Logic to fetch tokens and instantiate FacebookAdapter
    pass
```

### CLI Updates

Modify `src/sm_tracker/cli/__init__.py`:

- Add `"FACEBOOK_ACCESS_TOKEN"`, `"FACEBOOK_ID"` to `ENV_FIELD_SPECS`.
- (Future scope) Add OAuth flow to `auth` command for Facebook if requested.

Modify `src/sm_tracker/platforms/__init__.py`:

- Add `"facebook"` to `SUPPORTED_PLATFORM_NAMES`.
- Add `create_facebook_adapter` resolver mappings.
