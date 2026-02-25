# Specifications

Self-contained reference for building the social media following tracker CLI prototype.

## Tech Stack

| Layer     | Technology       | Notes                                                                                                                      |
| --------- | ---------------- | -------------------------------------------------------------------------------------------------------------------------- |
| CLI       | Typer            |                                                                                                                            |
| Storage   | libSQL           | SQLite-compatible, [tursodatabase/libsql](https://github.com/tursodatabase/libsql)                                         |
| Twitter   | Tweepy           | [tweepy/tweepy](https://github.com/tweepy/tweepy)                                                                          |
| Bluesky   | atproto          | [bluesky-social/atproto](https://github.com/bluesky-social/atproto)                                                        |
| Farcaster | Direct API       | Warpcast API (`api.warpcast.com`); farcaster-py archived. If user endpoint lacks counts, paginate `followers`/`following`. |
| Mastodon  | Mastodon.py      | [halcy/Mastodon.py](https://github.com/halcy/Mastodon.py)                                                                  |
| Threads   | meta-threads-sdk | [MetaThreads/meta-threads-sdk](https://github.com/MetaThreads/meta-threads-sdk)                                            |

**Python:** 3.12+ (required by meta-threads-sdk)

## Config & Credentials

Configuration is split into two files per best practice:

| File           | Purpose                                      | Location                                  |
| -------------- | -------------------------------------------- | ----------------------------------------- |
| `.env`         | API keys, tokens, secrets, account identifiers | Project dir or loaded from process env    |
| `config.toml`  | Paths, retention, log level, non-sensitive   | `~/.config/sm-tracker/config.toml` or project dir |

`.env` is never committed; `config.toml` may ship with defaults.

### Environment Variables (.env)

Sensitive values only. Loaded via `python-dotenv`.

| Variable                | Platform  | Required | Notes                                                                 |
| ----------------------- | --------- | -------- | --------------------------------------------------------------------- |
| `TWITTER_BEARER_TOKEN`  | Twitter   | Yes      | X Developer account                                                   |
| `TWITTER_HANDLE`        | Twitter   | Yes      | Account to track (e.g. `yourhandle`)                                  |
| `BLUESKY_HANDLE`        | Bluesky   | Yes      | Account to track; public profile needs no auth                        |
| `BLUESKY_APP_PASSWORD`  | Bluesky   | No       | Only if handle is private                                             |
| `FARCASTER_MNEMONIC`    | Farcaster | Yes      | Or private key for auth                                               |
| `FARCASTER_USERNAME`    | Farcaster | Yes      | Username to track (e.g. `yourname`)                                   |
| `MASTODON_ACCESS_TOKEN` | Mastodon  | Yes      | OAuth token                                                           |
| `MASTODON_INSTANCE`     | Mastodon  | Yes      | e.g. `mastodon.social`                                                |
| `THREADS_ACCESS_TOKEN`  | Threads   | Yes      | Meta OAuth token; requires `MANAGE_INSIGHTS` scope for follower count |
| `THREADS_USER_ID`       | Threads   | Yes      | User ID for `insights.get_user_insights()`                            |

### App Config (config.toml)

Non-sensitive settings. Parsed via `tomllib` (Python 3.11+). Lookup order: project dir, then `~/.config/sm-tracker/`.

**Profiles:** Use `[paths.<profile>]` and `[logging.<profile>]` for environment-specific config. Override via `SM_TRACKER_PROFILE` env var or `--profile` CLI flag. Default profile: `profile = "dev"` (or `"dev"` if omitted).

```toml
profile = "dev"

[paths.dev]
db = "./data-dev.db"
logs = "./logs-dev"

[paths.production]
db = "~/.local/share/sm-tracker/data.db"
logs = "~/.local/share/sm-tracker/logs"

[logging.dev]
retention_days = 7
level = "DEBUG"

[logging.production]
retention_days = 14
level = "INFO"
```

| Key                    | Default                    | Notes                            |
| ---------------------- | -------------------------- | -------------------------------- |
| `profile`              | `"dev"`                    | Active profile; override via env/flag |
| `paths.<profile>.db`   | `~/.local/share/sm-tracker/data.db` | Database file path for profile   |
| `paths.<profile>.logs` | `~/.local/share/sm-tracker/logs`   | Log directory for profile        |
| `logging.<profile>.retention_days` | 14               | Days of log backups to keep      |
| `logging.<profile>.level` | `INFO`                   | Log level                        |

### Account Identifiers (per platform)

| Platform  | Identifier       | Example                |
| --------- | ---------------- | ---------------------- |
| Twitter   | handle           | `yourhandle`           |
| Bluesky   | handle           | `you.bsky.social`      |
| Farcaster | username         | `yourname`             |
| Mastodon  | `@user@instance` | `@you@mastodon.social` |
| Threads   | username         | `yourname`             |

Identifiers stored in `.env` per the table above. Mastodon derives `@user@instance` from token/instance.

## Data Model

| Decision          | Choice                                              |
| ----------------- | --------------------------------------------------- |
| Metrics           | Followers and following                             |
| Account selection | Single user (expand to multiple profiles in future) |

## Database Schema

```sql
CREATE TABLE IF NOT EXISTS snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS counts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    snapshot_id INTEGER NOT NULL,
    platform TEXT NOT NULL,
    following_count INTEGER,  -- Nullable; some platforms don't expose
    follower_count INTEGER,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);
```

## Storage

| Decision         | Choice                     | Notes                                                         |
| ---------------- | -------------------------- | ------------------------------------------------------------- |
| DB file location | `config.toml` → `paths.db` | Default: `~/.local/share/sm-tracker/data.db`; overridable      |

## Tooling

| Decision             | Choice                         |
| -------------------- | ------------------------------ |
| Package/tool manager | mise (this machine only)       |
| Python deps & tasks  | uv                             |
| Test framework       | pytest                         |
| Linter               | ruff                           |
| Type checker         | mypy                           |
| Publishing           | Personal use only (for now)    |
| Pre-commit           | ruff, mypy, prettier, markdownlint-cli2 (local consistency) |

### Formatting & Linting

| Tool            | Purpose                                    |
| --------------- | ------------------------------------------ |
| ruff            | Python linting and formatting               |
| mypy            | Static type checking                        |
| .editorconfig   | Editor consistency (indent, charset, eol)   |
| prettier        | Markdown/YAML/JSON formatting (pre-commit)  |
| markdownlint-cli2 | Markdown linting (pre-commit)             |

### Git

| File           | Purpose                                                                 |
| -------------- | ----------------------------------------------------------------------- |
| `.gitattributes` | `* text=auto eol=lf` keeps LF in the repo; Git handles Windows conversion on checkout |

### Editor Consistency

`.editorconfig` enforces `end_of_line = lf`, charset, and indent rules at the root, with overrides for `*.md`, `*.py`, and `Makefile`. Editors that support EditorConfig apply these settings automatically.

### Tool Config (pyproject.toml)

```toml
[tool.ruff]
target-version = "py312"
line-length = 100

[tool.mypy]
python_version = "3.12"
strict = true
```

## Project Structure

```
src/sm_tracker/
├── __main__.py      # Entry point: python -m sm_tracker
├── cli/             # Typer commands
├── config/          # .env + config.toml loading and validation
├── db/              # libSQL connection, schema, queries
├── logging/         # Logging setup and utilities
├── platforms/       # Platform-specific fetchers (twitter, bluesky, etc.)
└── ...
```

**Package & binary name:** `sm-tracker`. Package uses `sm_tracker` (Python modules use underscores). Run via `sm-tracker` (after `pip install -e .`) or `python -m sm_tracker`. Configure in pyproject.toml:

```toml
[project.scripts]
sm-tracker = "sm_tracker.cli:app"
```

## CLI Commands

| Command   | Description                                                                                                                                        |
| --------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `track`   | Fetch current counts from all configured platforms, save to DB. Optional `--platform` / `-p`: run only for specified platform(s), can be repeated. |
| `show`    | Display latest snapshot with counts and deltas vs previous. Optional `--platform` / `-p`: show only specified platform(s), can be repeated.        |
| `history` | Show past snapshots (options: `--platform`, `--limit`)                                                                                             |
| `config`  | Guide for initial setup: create/validate `.env` (credentials) and `config.toml` (paths, retention), document required variables per platform. |
| `help`    | Show command usage and available options.                                                                                                          |

**Multiple platforms example:**

```bash
sm-tracker track -p twitter -p bluesky
sm-tracker show -p twitter -p bluesky
```

**Output:** Plain text (no Rich).

### Output Format (show)

| Scenario                  | Format           |
| ------------------------- | ---------------- |
| First snapshot (no delta) | `132 (N/A)`      |
| Positive delta            | `132 (+10)`      |
| Negative delta            | `132 (-1)`       |
| Zero delta                | `132 (0)`        |
| Platform has no following | `Following: N/A` |

### Empty-State Messages

| Command   | Condition               | Message                                                     |
| --------- | ----------------------- | ----------------------------------------------------------- |
| `track`   | No platforms configured | "Add at least one platform via `sm-tracker config` or .env (credentials)" |
| `show`    | No data yet             | "No snapshots yet. Run `sm-tracker track` first."           |
| `history` | No data yet             | "No history yet. Run `sm-tracker track` first."             |

## Logging

| Setting      | Choice                                                                 |
| ------------ | ---------------------------------------------------------------------- |
| Location     | `config.toml` → `paths.logs` (default: `~/.local/share/sm-tracker/logs`) |
| Filename     | `sm-tracker.log`                                                       |
| Format       | Human-readable: `%(asctime)s - %(name)s - %(levelname)s - %(message)s` |
| Timestamp    | ISO 8601: `%Y-%m-%dT%H:%M:%S`                                          |
| Rotation     | `TimedRotatingFileHandler`, daily at midnight                          |
| Backup count | `config.toml` → `logging.retention_days` (default: 14)                 |
| Output       | File + console (both)                                                  |

Create log directory if it doesn't exist.

## CI

| Setting  | Choice                                             |
| -------- | -------------------------------------------------- |
| Platform | GitHub Actions                                     |
| Jobs     | Run pytest (tests), ruff (lint), mypy (type check) |

## Error Handling

| Scenario                                     | Behavior                                            |
| -------------------------------------------- | --------------------------------------------------- |
| Missing credentials for a platform           | Skip that platform, continue with others            |
| Platform fetch fails (rate limit, API error) | Log/warn, continue with others, partial snapshot OK |
| No previous snapshot                         | Show current counts with `(N/A)` for delta          |

### Output Format (history)

Plain-text table, columns: `Date | Platform | Followers | Following | Delta`. Same delta rules as `show` (N/A, +n, -n, 0). Platform with no following shows `N/A`.
