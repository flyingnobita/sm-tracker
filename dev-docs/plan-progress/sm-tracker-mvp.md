# Progress: sm-tracker MVP

Plan: [20250225-PLANS-sm-tracker-mvp.md](../20250225-PLANS-sm-tracker-mvp.md)

## Phase 1: Project Scaffolding

- [x] `pyproject.toml` with deps, ruff, mypy config
- [x] `mise.toml` tool versions and tasks
- [x] `src/sm_tracker/` package layout
- [x] `.gitattributes`, `.editorconfig`
- [x] `.env.example`, `config.toml.example`
- [x] Verify: package imports, `ruff check`, `mypy`

## Phase 2: Config & Logging

- [x] `.env` loading (`python-dotenv`)
- [x] `config.toml` parsing (`tomllib`) with profile support
- [x] Config validation and defensive error handling
- [x] Logging: file + console, daily rotation, retention
- [x] Tests: config loading, profile resolution, log output

## Phase 3: Database Layer

- [x] libSQL connection management
- [x] Schema init (`snapshots`, `counts`)
- [x] Query functions (insert, fetch latest, fetch history)
- [x] Tests: CRUD, edge cases

## Phase 4: CLI Skeleton

- [x] Typer app with command stubs
- [x] Platform flag parsing (`-p`, repeatable)
- [x] Entry point wiring (`[project.scripts]`)
- [x] Tests: CLI invocation, flags, help, empty-state messages

## Phase 5: First Platform Adapter (Bluesky)

- [x] `platforms/bluesky.py` with public profile fetch
- [x] Platform adapter interface/protocol
- [x] Wire `track` + `show` end-to-end
- [x] Tests: mocked API, integration flow

## Phase 6: Remaining Platform Adapters

- [x] Twitter (Tweepy)
- [x] Mastodon (Mastodon.py)
- [x] Farcaster (Warpcast API)
- [x] Threads (meta-threads-sdk)
- [x] Tests: per-adapter unit tests plus real-credential verification test for each adapter

## Phase 7: Output Formatting & Edge Cases

- [x] Delta display rules (N/A, +n, -n, 0)
- [x] History plain-text table
- [x] Error handling: skip + warn, partial snapshots
- [x] Tests: formatting, error/skip scenarios

## Phase 8: Config Command

- [ ] Guided `.env` setup
- [ ] Guided `config.toml` setup
- [ ] Validation and warnings
- [ ] Tests: creation, validation, guided flow

## Phase 9: CI & Quality

- [ ] GitHub Actions workflow
- [ ] Pre-commit hooks
- [ ] All tests green, no lint/type errors

## Phase 10: Documentation

- [ ] README with installation and usage
- [ ] Onboarding guide
- [ ] Config reference
- [ ] Link checking, markdown lint clean
