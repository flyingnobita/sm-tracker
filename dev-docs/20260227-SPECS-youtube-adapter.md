# SPECS: YouTube Subscriber Tracking

Date: 2026-02-27
Status: Proposed

## Context

Issue #6 requests tracking YouTube channel subscriber counts in sm-tracker.

## Behavior

- Add a new platform adapter `youtube` that conforms to `sm_tracker.platforms.PlatformAdapter`.
- Configuration will be provided via environment variables:
    - `YOUTUBE_API_KEY`: Required. The Google Cloud API key with YouTube Data API v3 enabled.
    - `YOUTUBE_HANDLE`: Optional. The YouTube handle (e.g. `@channel`) to track.
    - `YOUTUBE_CHANNEL_ID`: Optional. The YouTube channel ID to track.
    - One of `YOUTUBE_HANDLE` or `YOUTUBE_CHANNEL_ID` must be provided. If both are provided, `YOUTUBE_CHANNEL_ID` takes precedence.
- Data will be fetched using the YouTube Data API v3:
    - Endpoint for handle: `https://www.googleapis.com/youtube/v3/channels?part=statistics&forHandle={handle}&key={api_key}`
    - Endpoint for channel ID: `https://www.googleapis.com/youtube/v3/channels?part=statistics&id={channel_id}&key={api_key}`
- The adapter will return a `PlatformCounts` object:
    - `platform`: `"youtube"`
    - `follower_count`: Parsed from `items[0].statistics.subscriberCount`
    - `following_count`: `None` (YouTube does not expose subscription counts via this endpoint in a meaningful way for our use case).

## Constraints

- Standard library only (`urllib.request` and `json`), mirroring the implementation style of the `farcaster` adapter.
- Handle missing responses, no items returned, and network timeouts gracefully using standard API patterns in the system.
- Update `SUPPORTED_PLATFORM_NAMES` and factories in `src/sm_tracker/platforms/__init__.py`.
