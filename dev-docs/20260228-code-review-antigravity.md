# sm-tracker Codebase Review

Date: 2026-02-28
Reviewer: Antigravity

## Overview

The `sm-tracker` codebase is a well-structured Python CLI application designed to track follower and following counts across multiple social media platforms. It utilizes modern Python (3.12+), strong static typing (`mypy`), and excellent tooling (`mise`, `uv`, `pytest`, `ruff`).

## 1. Architecture & Design

The architecture follows a clear separation of concerns:

- **CLI (`src/sm_tracker/cli/`)**: Built with `typer`, handles user input, environment loading, and presentation logic.
- **Config (`src/sm_tracker/config/`)**: Manages `config.toml`, `.env`, and profile resolution (`dev` vs `production`).
- **DB (`src/sm_tracker/db/`)**: Handles persistence using `libsql-client`, with a simple schema of `snapshots` and `counts`.
- **Platforms (`src/sm_tracker/platforms/`)**: Implements an adapter pattern (`PlatformAdapter` Protocol) to fetch data from various APIs.

**Strengths:**

- **Adapter Pattern**: The `PlatformAdapter` protocol is excellent. It allows for easy addition of new platforms without modifying core logic.
- **Dependency Management**: Utilizing `uv` and `mise` provides a very fast and reproducible development environment. The `mise.toml` defines tasks clearly.
- **Environment Handling**: The config system smoothly gracefully degrades from explicit CLI arguments, to `.env`, to `config.toml`, to default values.

**Areas for Improvement:**

- **CLI Module Size**: `src/sm_tracker/cli/__init__.py` is currently over 900 lines long. It contains all commands (`track`, `show`, `history`, `config`, `auth`) and their helper functions.
  _Recommendation:_ Split the CLI commands into separate modules (e.g., `src/sm_tracker/cli/track.py`, `src/sm_tracker/cli/auth.py`) and use a Typer sub-application or just import them into the main `app`.
- **Database Migrations**: The database schema is initialized using `CREATE TABLE IF NOT EXISTS`. While sufficient for the current MVP size, any future schema changes (adding new columns, indexes, or relationships) will be difficult.
  _Recommendation:_ Introduce a lightweight migration tool like `alembic` or simple versioned SQL scripts if the database complexity increases.

## 2. Platform Adapters

The adapters in `src/sm_tracker/platforms/` represent the core value of the tool.

**Strengths:**

- Clear return types using the `PlatformCounts` dataclass.
- Each adapter safely extracts values and standardizes on returning `follower_count` and `following_count` (which may be `None`).
- Graceful error handling in `resolve_adapters()`.

**Areas for Improvement:**

- **Inconsistent HTTP Libraries**: While some adapters use official SDKs (e.g., `tweepy` for Twitter, `meta-threads-sdk` for Threads), others use manual HTTP requests. For instance, `youtube.py` uses the standard library `urllib.request`.
  _Recommendation:_ While `urllib` keeps dependencies low, consider standardizing on a robust HTTP client like `httpx` for any manual calls to benefit from connection pooling, better timeout handling, and simpler JSON parsing.
- **Error Handling Granularity**: Adapters might throw various types of network or parsing errors during `fetch_counts()`. The `track` command catches the generic `Exception` to prevent one failing platform from crashing the whole execution. This is good for resilience, but it can mask deeper bugs.

## 3. Database Layer

**Strengths:**

- Using `libsql-client` allows seamless transition between a local SQLite file (`data-dev.db`) and a remote Turso database, which is a great architectural choice for CLI tools.
- Data classes (`Snapshot`, `CountRow`) keep the data structures clean between the DB layer and CLI layer.

## 4. Testing & Code Quality

- **Static Analysis**: The codebase passes `ruff` (formatting and linting) and strict `mypy` checks.
- **Tests**: 92 tests passed via `pytest`. This indicates a very high level of test coverage and TDD adherence.
- **Documentation**: The use of `.md` documentation sets a great standard, and markdown checking is enforced via `markdownlint`.

## Conclusion

The `sm-tracker` codebase is in excellent shape. It reflects high standards of modern Python engineering. The highest priority technical debt to address in the near future is splitting up the large `cli/__init__.py` file to maintain readability. Aside from that, the application is robust, strictly typed, and easily extensible.
