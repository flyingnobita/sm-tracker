# Implementation Plan: sm-tracker MVP

Date: 2025-02-25
Status: Active

## References

- **PRD:** [PRD.md](PRD.md)
- **Spec:** [20250225-SPECS-sm-tracker-mvp.md](20250225-SPECS-sm-tracker-mvp.md)
- **Progress:** [plan-progress/sm-tracker-mvp.md](plan-progress/sm-tracker-mvp.md)

## SDD Workflow

Each phase follows: **Spec -> Tests -> Code -> Verify**

- Write/reference the spec section for the feature
- Write failing tests that encode the spec's behavior
- Implement until tests pass
- Verify via `pytest`, `ruff`, `mypy`

## Goals

- Deliver a working CLI (`sm-tracker`) that tracks follower/following counts across Twitter/X, Bluesky, Farcaster, Mastodon, and Threads
- Local persistence via libSQL, plain-text output, automation-friendly
- Full test coverage, CI pipeline, and documentation

## Phases

### Phase 1: Project Scaffolding

**Spec refs:** Tech Stack, Tooling, Project Structure

1. `pyproject.toml` - uv, pytest, ruff, mypy, deps, `[tool.ruff]`, `[tool.mypy]`
2. `mise.toml` - tool versions and tasks
3. `src/sm_tracker/` package layout with `__init__.py` files
4. `.gitattributes` - LF line endings
5. `.editorconfig` - indent, charset, eol
6. `.env.example` - credentials template
7. `config.toml.example` - app config template

**Tests:** Verify package imports, config file loading stubs
**Done when:** `uv run python -m sm_tracker` executes without error, `ruff check` and `mypy` pass

### Phase 2: Config & Logging

**Spec refs:** Config & Credentials, Logging

1. `src/sm_tracker/config/` - `.env` loading via `python-dotenv`, `config.toml` parsing via `tomllib`
2. Profile support (`dev` / `production`) with env var and CLI flag override
3. Config validation and defensive error handling for missing/incomplete files
4. `src/sm_tracker/logging/` - file + console output, `TimedRotatingFileHandler`, daily rotation, configurable retention

**Tests:** Config loading (valid, missing, partial), profile resolution, log output to both file and console, rotation behavior
**Done when:** All config/logging tests pass, `ruff check` and `mypy` clean

### Phase 3: Database Layer

**Spec refs:** Database Schema, Data Model, Storage

1. `src/sm_tracker/db/` - libSQL connection management
2. Schema initialization (`snapshots`, `counts` tables)
3. Query functions: insert snapshot, insert counts, fetch latest, fetch history

**Tests:** Schema creation, CRUD operations, edge cases (empty DB, duplicate snapshots)
**Done when:** All DB tests pass against an in-memory or temp-file libSQL instance

### Phase 4: CLI Skeleton

**Spec refs:** CLI Commands, Empty-State Messages

1. Typer app in `src/sm_tracker/cli/`
2. Command stubs: `track`, `show`, `history`, `config`, `help`
3. Platform flag parsing (`-p` / `--platform`, repeatable)
4. Entry point wiring: `sm-tracker` binary via `pyproject.toml` `[project.scripts]`

**Tests:** CLI invocation, flag parsing, help output, empty-state messages
**Done when:** All commands respond correctly to `--help`, flag parsing works, empty-state messages display

### Phase 5: First Platform Adapter (Bluesky)

**Spec refs:** Tech Stack (atproto), Config & Credentials (Bluesky vars)

1. `src/sm_tracker/platforms/bluesky.py` - public profile fetch, optional auth
2. Platform adapter interface/protocol for consistent API across adapters
3. Wire `track` and `show` commands end-to-end for Bluesky

**Tests:** Adapter unit tests (mocked API responses), integration test for track -> show flow
**Done when:** `sm-tracker track -p bluesky` fetches and stores counts, `sm-tracker show -p bluesky` displays with deltas

### Phase 6: Remaining Platform Adapters

**Spec refs:** Tech Stack (per-platform libraries), Config & Credentials (per-platform vars)

1. `src/sm_tracker/platforms/twitter.py` - Tweepy, bearer token auth
2. `src/sm_tracker/platforms/mastodon.py` - Mastodon.py, OAuth token
3. `src/sm_tracker/platforms/farcaster.py` - direct Warpcast API, paginate if needed
4. `src/sm_tracker/platforms/threads.py` - meta-threads-sdk, `MANAGE_INSIGHTS` scope

**Tests:** Per-adapter unit tests (mocked API responses), missing-credential skip behavior
**Done when:** Each adapter passes its tests, `track` and `show` work for all platforms

### Phase 7: Output Formatting & Edge Cases

**Spec refs:** Output Format (show), Output Format (history), Empty-State Messages, Error Handling

1. Delta display rules: `N/A`, `+n`, `-n`, `0`
2. `Following: N/A` for platforms that don't expose it
3. History plain-text table: `Date | Platform | Followers | Following | Delta`
4. Graceful handling: missing credentials (skip + warn), API errors (log + continue), partial snapshots

**Tests:** Delta calculation, formatting output strings, error/skip scenarios
**Done when:** All output formatting tests pass, error handling is verified

### Phase 8: Config Command

**Spec refs:** CLI Commands (config), Config & Credentials

1. Guided `.env` setup - prompt for credentials per platform
2. Guided `config.toml` setup - paths, retention, profile
3. Validation of existing files, warnings for missing/invalid values

**Tests:** Config file creation, validation, guided flow (simulated input)
**Done when:** `sm-tracker config` creates valid `.env` and `config.toml`, validation catches errors

### Phase 9: CI & Quality

**Spec refs:** CI, Tooling

1. GitHub Actions workflow: `pytest`, `ruff`, `mypy` on push/PR
2. Pre-commit hooks: ruff, mypy, prettier, markdownlint-cli2
3. Final pass: ensure all tests green, no lint/type errors

**Tests:** CI pipeline runs successfully on a test push
**Done when:** CI pipeline green, all checks pass locally and in CI

### Phase 10: Documentation

**Spec refs:** PRD (User Experience, Onboarding)

1. README - installation, quickstart, usage examples for all commands
2. Onboarding guide - platform-by-platform credential setup
3. Config reference - all `.env` vars and `config.toml` keys

**Tests:** Link checking, markdown linting
**Done when:** README is complete, all links valid, markdown lint clean
