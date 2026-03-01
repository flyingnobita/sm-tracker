# Configuration Reference

`sm-tracker` reads configuration from two files:

- `.env` for secrets and account identifiers
- `config.toml` for non-sensitive runtime settings

## Load order

1. `.env`: current working directory (loaded by `python-dotenv`)
2. `config.toml`: current working directory, then `~/.config/sm-tracker/config.toml`

## `.env` reference

### Twitter/X

> **Note:** The Twitter/X API requires a paid Basic tier subscription or higher. The Free tier is not sufficient.

- `TWITTER_BEARER_TOKEN` (required)
- `TWITTER_HANDLE` (required)

### Bluesky

- `BLUESKY_HANDLE` (required)
- `BLUESKY_APP_PASSWORD` (optional)

### Farcaster

- `FARCASTER_API_KEY` (required)
- `FARCASTER_USERNAME` (required)

### Mastodon

- `MASTODON_ACCESS_TOKEN` (required)
- `MASTODON_INSTANCE` (required; for example `mastodon.social`)

### Threads

- `THREADS_ACCESS_TOKEN` (required)
- `THREADS_USER_ID` (required)
- `THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC` (optional, ISO UTC timestamp)
- `THREADS_APP_ID` (optional, needed for `auth`)
- `THREADS_APP_SECRET` (optional, needed for `auth`)
- `THREADS_REDIRECT_URI` (optional, default: `https://localhost/callback`)

### Facebook

To collect Page metrics, you need a **Page Access Token**. You have two options for configuring this:

**Option 1: Direct Page Token (Recommended)**

1. Provide `FACEBOOK_PAGE_ACCESS_TOKEN` in your `.env`.
2. `FACEBOOK_ID` can optionally be omitted, as the app will automatically fetch the ID of the page the token belongs to.

**Option 2: Automatic Token Exchange**

1. Generate a generic **User Access Token** in the Meta App Dashboard.
2. Provide this via `FACEBOOK_ACCESS_TOKEN`.
3. You MUST provide the specific `FACEBOOK_ID` of your page.
4. The tracker will seamlessly use the User Token to query the Graph API and extract the correct Page Access Token for your `FACEBOOK_ID` in the background.

## `config.toml` reference

### Required shape

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

### Keys

- `profile`
    - Active profile to use
    - Allowed values: `dev`, `production`
    - Default: `dev`

- `[paths.<profile>].db`
    - Database file path for that profile
    - Required for active profile

- `[paths.<profile>].logs`
    - Log directory path for that profile
    - Required for active profile

- `[logging.<profile>].retention_days`
    - Number of rotated log files to keep
    - Must be a positive integer

- `[logging.<profile>].level`
    - Log verbosity
    - Supported values: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`

## Validation behavior

- Missing `.env` or `config.toml` produces warnings in `sm-tracker config` and files can be created by the wizard.
- Missing required env vars do not crash the CLI; affected platforms are skipped with warnings.
- Invalid `config.toml` values produce clear error messages and prevent loading that config.

## Examples

Track only configured platforms:

```bash
sm-tracker track -p twitter -p mastodon
```

Run guided validation again after editing:

```bash
sm-tracker config
```

## Output format flags

The `track`, `show`, and `history` commands support machine-readable output:

- `--json`: emit JSON arrays (uses `null` for missing values)
- `--csv`: emit CSV rows with a header (uses empty strings for missing values)

`--json` and `--csv` are mutually exclusive.
