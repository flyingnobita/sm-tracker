# Build Plan: sm-tracker MVP

Suggested implementation order for the social media tracker CLI.

## Build Order

1. **Project scaffolding**
   - `pyproject.toml` (uv, pytest, ruff, mypy, deps, `[tool.ruff]`, `[tool.mypy]`)
   - `mise.toml` (tool versions, tasks)
   - `src/sm_tracker/` package layout
   - `.env.example` (exists; update as needed)

2. **Config & logging**
   - `src/sm_tracker/config/` — `.env` loading, validation
   - `src/sm_tracker/logging/` — file + console, daily rotation, retention

3. **Database layer**
   - `src/sm_tracker/db/` — libSQL connection, schema init, queries
   - Snapshots and counts tables

4. **CLI skeleton**
   - Typer app in `src/sm_tracker/cli/`
   - `track`, `show`, `history`, `config`, `help` stubs
   - Platform flag parsing (`-p` repeatable)

5. **First platform adapter (Bluesky)**
   - Public profile, minimal auth
   - `src/sm_tracker/platforms/bluesky.py`
   - Wire `track` and `show` for Bluesky only

6. **Remaining platform adapters**
   - Twitter (Tweepy)
   - Mastodon (Mastodon.py)
   - Farcaster (direct Warpcast API)
   - Threads (meta-threads-sdk, MANAGE_INSIGHTS)

7. **Empty-state and output formatting**
   - Implement delta rules (N/A, +n, -n, 0)
   - Empty-state messages for track/show/history

8. **Config command**
   - Guided `.env` setup and validation

9. **Tests & CI**
   - Unit tests for commands, platform adapters, db
   - GitHub Actions workflow (pytest, ruff, mypy)

10. **Documentation**
    - README, onboarding, usage examples
