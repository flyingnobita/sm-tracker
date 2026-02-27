# Implementation Plan: Facebook Tracker

Date: 2026-02-27
Status: Proposed

## Context

Add Facebook support to the `sm-tracker` CLI following the specification outlined in `20260227-SPECS-facebook-tracker.md`.

## Proposed Changes

1. **Dependency Installation**
    - None needed. We will use Python's built-in `urllib.request`.

2. **Facebook Adapter Core (`src/sm_tracker/platforms/facebook.py`)**
    - Import necessary utilities.
    - Define `FacebookAdapter` dataclass with `target_id` and `access_token` fields.
    - Implement `fetch_counts` method to call the Graph API: `https://graph.facebook.com/v19.0/{target_id}?fields=followers_count,fan_count,member_count&access_token={access_token}`. (Note: `fan_count` usually maps to page likes, while `followers_count` maps to actual followers, `member_count` for groups).
    - Define `create_facebook_adapter(env_map)` to instantiate the adapter from the environment variables `FACEBOOK_ACCESS_TOKEN` and `FACEBOOK_ID`.

3. **Adapter Registration (`src/sm_tracker/platforms/__init__.py`)**
    - Add `"facebook"` to `SUPPORTED_PLATFORM_NAMES`.
    - Add `"facebook": create_facebook_adapter` mapping inside `resolve_adapters`.
    - Update imports to include Facebook adapter factory.

4. **CLI Updates (`src/sm_tracker/cli/__init__.py`)**
    - Update `ENV_FIELD_SPECS` to include:
        - `("FACEBOOK_ACCESS_TOKEN", "Facebook Page/User/Group access token", True)`
        - `("FACEBOOK_ID", "Facebook Target ID", True)`
    - Update `_validate_required_env_values` to add Facebook missing value validation (`"facebook": ["FACEBOOK_ACCESS_TOKEN", "FACEBOOK_ID"]`).

## Verification Plan

### Automated Tests

1. Add `tests/test_phase6_facebook.py` using `pytest`.
2. Use `unittest.mock.patch` to mock `urllib.request.urlopen` to avoid real network calls.
3. Test success scenario: Return mocked payload `{"id": "123", "followers_count": 1000, "fan_count": 900}` or `{"id": "123", "member_count": 500}`.
4. Test missing credentials scenario where `FACEBOOK_ACCESS_TOKEN` or `FACEBOOK_ID` is missing in `env` (should raise config error or return warning).
5. Test platform factory registration.

Run tests using:

```bash
uv run pytest tests/test_phase6_facebook.py
```
