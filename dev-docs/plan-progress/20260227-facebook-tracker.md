# Facebook Tracker: Plan Progress

Date: 2026-02-27
Status: In Progress

## Spec

- [x] Write specifications
- [x] Write implementation plan
- [x] Setup plan progress doc

## Tests

- [x] Create `tests/test_phase6_facebook.py`
    - [x] Mock `urllib.request.urlopen` to test successful Graph API response
    - [x] Test missing credentials `FACEBOOK_ACCESS_TOKEN` / `FACEBOOK_ID`
    - [x] Verify `PlatformCounts` structure
- [x] Ensure all tests pass (`uv run pytest tests/test_phase6_facebook.py`)

## Implementation

- [x] Create `src/sm_tracker/platforms/facebook.py`
- [x] Register in `src/sm_tracker/platforms/__init__.py`
- [x] Register ENV variables in `src/sm_tracker/cli/__init__.py`

## Validation

- [x] Complete test suite runs without errors (`pytest tests`)
- [x] `sm-tracker config` includes Facebook fields correctly
- [x] Manual test: Test with mock data / user credentials if provided
