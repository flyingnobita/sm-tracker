# PLANS: YouTube Subscriber Tracking

Date: 2026-02-27
Status: Completed

## Context

Issue #6 requests tracking YouTube channel subscriber counts in sm-tracker.

## Action Plan

1. **Configuration (`.env` & `config.toml.example`)**
    - Add `YOUTUBE_API_KEY` to `.env.example`.
    - Add `YOUTUBE_HANDLE` and `YOUTUBE_CHANNEL_ID` to `.env.example` as mutually exclusive options.

2. **Adapter Implementation (`src/sm_tracker/platforms/youtube.py`)**
    - Create a new `YouTubeAdapter` class conforming to `PlatformAdapter`.
    - Use `urllib.request` to query the YouTube Data API v3 (`https://www.googleapis.com/youtube/v3/channels`).
    - Extract `subscriberCount` from the statistics block. Return `None` for `following_count`.

3. **Adapter Registration (`src/sm_tracker/platforms/__init__.py`)**
    - Import `create_youtube_adapter`.
    - Add `"youtube"` to `SUPPORTED_PLATFORM_NAMES`.
    - Add the factory to the `factories` dictionary in `resolve_adapters`.

4. **Testing (`tests/platforms/test_youtube.py`)**
    - Add unit tests verifying:
        - Initialization with handle or channel ID.
        - Validation error if neither or `API_KEY` is missing.
        - Successful parsing of the API response (mocked `urlopen`).
        - Safe handling of empty or error responses.

5. **Verification**
    - Run `pytest tests/platforms/test_youtube.py`.
    - Ensure the linter (`ruff` / `mypy`) passes.
