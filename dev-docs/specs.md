# Specifications

Self-contained reference for building the social media following tracker CLI prototype.

## Tech Stack

| Layer     | Technology       | Notes                                                                              |
| --------- | ---------------- | ---------------------------------------------------------------------------------- |
| CLI       | Typer            |                                                                                    |
| Storage   | libSQL           | SQLite-compatible, [tursodatabase/libsql](https://github.com/tursodatabase/libsql) |
| Twitter   | Tweepy           | [tweepy/tweepy](https://github.com/tweepy/tweepy)                                  |
| Bluesky   | atproto          | [bluesky-social/atproto](https://github.com/bluesky-social/atproto)                |
| Farcaster | farcaster-py     | Archived, [a16z/farcaster-py](https://github.com/a16z/farcaster-py)                |
| Mastodon  | Mastodon.py      | [halcy/Mastodon.py](https://github.com/halcy/Mastodon.py)                          |
| Threads   | meta-threads-sdk | [MetaThreads/meta-threads-sdk](https://github.com/MetaThreads/meta-threads-sdk)    |

**Python:** 3.10+

## Config & Credentials

| Decision      | Choice | Notes                                                                                                                    |
| ------------- | ------ | ------------------------------------------------------------------------------------------------------------------------ |
| Config format | `.env` | API keys stored in config. **Note:** Move to `~/.config/sm-tracker/config.toml` for global CLI compatibility when ready. |

### Environment Variables (.env)

| Variable                | Platform  | Required | Notes                                     |
| ----------------------- | --------- | -------- | ----------------------------------------- |
| `TWITTER_BEARER_TOKEN`  | Twitter   | Yes      | X Developer account                       |
| `BLUESKY_HANDLE`        | Bluesky   | No       | Public profile, no auth needed for counts |
| `BLUESKY_APP_PASSWORD`  | Bluesky   | No       | Only if handle is private                 |
| `FARCASTER_MNEMONIC`    | Farcaster | Yes      | Or private key for auth                   |
| `MASTODON_ACCESS_TOKEN` | Mastodon  | Yes      | OAuth token                               |
| `MASTODON_INSTANCE`     | Mastodon  | Yes      | e.g. `mastodon.social`                    |
| `THREADS_ACCESS_TOKEN`  | Threads   | Yes      | Meta OAuth token                          |
| `DB_PATH`               | —         | No       | Default: `./data.db` in project dir       |
| `LOG_RETENTION_DAYS`    | —         | No       | Default: 14. Days of log backups to keep. |

### Account Identifiers (per platform)

| Platform  | Identifier       | Example                |
| --------- | ---------------- | ---------------------- |
| Twitter   | handle           | `yourhandle`           |
| Bluesky   | handle           | `you.bsky.social`      |
| Farcaster | username         | `yourname`             |
| Mastodon  | `@user@instance` | `@you@mastodon.social` |
| Threads   | username         | `yourname`             |

Store identifiers in `.env` (e.g. `TWITTER_HANDLE`, `BLUESKY_HANDLE`, etc.) or derive from auth where possible.

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
    following_count INTEGER NOT NULL,
    follower_count INTEGER,
    FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
);
```

## Storage

| Decision         | Choice      | Notes                                                                                                       |
| ---------------- | ----------- | ----------------------------------------------------------------------------------------------------------- |
| DB file location | Project dir | **Note:** Move to a more appropriate place (e.g. `~/.local/share/sm-tracker/`) after prototype is finished. |

## Tooling

| Decision              | Choice                      |
| --------------------- | --------------------------- |
| Dependency management | uv                          |
| Publishing            | Personal use only (for now) |

## Project Structure

```
src/sm_tracker/
├── __main__.py      # Entry point: python -m sm_tracker
├── cli/             # Typer commands
├── config/          # .env loading and validation
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
| `config`  | Guide for initial setup: create/validate `.env`, document required variables and account identifiers per platform.                                 |
| `help`    | Show command usage and available options.                                                                                                          |

**Multiple platforms example:**

```bash
sm-tracker track -p twitter -p bluesky
sm-tracker show -p twitter -p bluesky
```

**Output:** Plain text (no Rich).

## Logging

| Setting      | Choice                                                                 |
| ------------ | ---------------------------------------------------------------------- |
| Location     | `logs/` folder                                                         |
| Filename     | `sm-tracker.log`                                                       |
| Format       | Human-readable: `%(asctime)s - %(name)s - %(levelname)s - %(message)s` |
| Timestamp    | ISO 8601: `%Y-%m-%dT%H:%M:%S`                                          |
| Rotation     | `TimedRotatingFileHandler`, daily at midnight                          |
| Backup count | 14 days (configurable via `LOG_RETENTION_DAYS`)                        |
| Output       | File + console (both)                                                  |

Create `logs/` if it doesn't exist.

## Error Handling

| Scenario                                     | Behavior                                            |
| -------------------------------------------- | --------------------------------------------------- |
| Missing credentials for a platform           | Skip that platform, continue with others            |
| Platform fetch fails (rate limit, API error) | Log/warn, continue with others, partial snapshot OK |
| No previous snapshot                         | Show current counts only, no delta                  |
