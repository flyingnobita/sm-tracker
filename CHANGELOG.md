# Changelog

- Feb-26, 2026 - 12:47 PM +08 - Completed Phase 10 documentation by expanding README installation and usage guidance, adding a dedicated onboarding guide, adding a full configuration reference for `.env` and `config.toml`, and validating markdown/link consistency.
- Feb-26, 2026 - 12:44 PM +08 - Completed Phase 9 by validating CI quality gates (`pytest`, `ruff`, `mypy`, Prettier, markdownlint), aligning pre-commit hooks to run ruff/mypy/prettier/markdownlint-cli2 directly, and confirming Phase 8 config-command coverage remains green.
- Feb-26, 2026 - 12:35 PM +08 - Completed Phase 7 by adding Delta output to `history`, tightening track partial-snapshot messaging to only successful platforms, and adding dedicated formatting plus error/skip tests.
- Feb-26, 2026 - 11:56 AM +08 - Completed Phase 6 by validating Threads plus Twitter, Mastodon, and Farcaster adapters with unit and CLI integration coverage, and confirmed opt-in real-credential verification tests for all adapters.
- Feb-26, 2026 - 01:05 AM +08 - Added concrete Phase 2 runtime logging events for CLI startup plus track/show/history lifecycle, warning, and error paths, and expanded tests to assert emitted log content.
- Feb-26, 2026 - 01:00 AM +08 - Wired Phase 2 logging bootstrap into CLI startup so commands initialize file and console logging from `config.toml`, and added a CLI-level test proving `sm-tracker.log` is created in the configured logs path.
- Feb-26, 2026 - 12:06 AM +08 - Completed Phase 3 database layer with libSQL connection helpers, schema initialization, query APIs, and CRUD plus edge-case tests.
- Feb-26, 2026 - 12:06 AM +08 - Completed Phase 4 CLI skeleton with Typer command stubs, repeatable platform flags, and CLI tests.
- Feb-26, 2026 - 12:09 AM +08 - Completed Phase 2 config and logging with .env/config.toml profile resolution, defensive validation, rotating file plus console logging, and full Phase 2 tests.
- Feb-26, 2026 - 12:17 AM +08 - Completed Phase 5 with a Bluesky adapter, shared adapter protocol, end-to-end `track`/`show` DB wiring, and mocked adapter plus CLI integration tests.
- Feb-25, 2025 - 12:00 PM UTC - CI and pre-commit aligned: ruff check+format, mypy src/, prettier, markdownlint-cli2; shared .markdownlint-cli2.yaml
- Feb-25, 2025 - 12:00 PM UTC - config.toml: profile support (`paths.<profile>`, `logging.<profile>`), default profile `dev`
- Feb-25, 2025 - 12:00 PM UTC - Config split: `.env` for API keys/secrets, `config.toml` for paths/retention (specs, PRD, plans, README)
- Feb-25, 2025 - 12:00 PM UTC - Pre-build spec consolidation: Python 3.12, Farcaster direct API, env vars, output format, empty states, tooling (pytest/ruff/mypy), mise+uv, CI, plans.md
