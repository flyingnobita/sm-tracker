# Changelog

- Feb-26, 2026 - 12:06 AM +08 - Completed Phase 3 database layer with libSQL connection helpers, schema initialization, query APIs, and CRUD plus edge-case tests.
- Feb-26, 2026 - 12:06 AM +08 - Completed Phase 4 CLI skeleton with Typer command stubs, repeatable platform flags, and CLI tests.
- Feb-26, 2026 - 12:09 AM +08 - Completed Phase 2 config and logging with .env/config.toml profile resolution, defensive validation, rotating file plus console logging, and full Phase 2 tests.
- Feb-26, 2026 - 12:17 AM +08 - Completed Phase 5 with a Bluesky adapter, shared adapter protocol, end-to-end `track`/`show` DB wiring, and mocked adapter plus CLI integration tests.
- Feb-25, 2025 - 12:00 PM UTC - CI and pre-commit aligned: ruff check+format, mypy src/, prettier, markdownlint-cli2; shared .markdownlint-cli2.yaml
- Feb-25, 2025 - 12:00 PM UTC - config.toml: profile support (`paths.<profile>`, `logging.<profile>`), default profile `dev`
- Feb-25, 2025 - 12:00 PM UTC - Config split: `.env` for API keys/secrets, `config.toml` for paths/retention (specs, PRD, plans, README)
- Feb-25, 2025 - 12:00 PM UTC - Pre-build spec consolidation: Python 3.12, Farcaster direct API, env vars, output format, empty states, tooling (pytest/ruff/mypy), mise+uv, CI, plans.md
