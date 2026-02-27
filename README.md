# Social Media Tracker (sm-tracker)

![sm-tracker banner](assets/sm-tracker-banner.jpeg)

`sm-tracker` is a CLI that tracks follower and following counts across 🐦 Twitter/X, 🦋 Bluesky, 🛰️ Farcaster, 🐘 Mastodon, and 🧵 Threads.

`sm-tracker` stores social-metric snapshots in libSQL (local SQLite-compatible by default), prints human-readable output by default, and supports JSON/CSV for scripts, cron jobs, and AI-agent automation.

## ✅ Requirements

- Python 3.12+
- `uv`
- API credentials in `.env`
- Runtime settings in `config.toml`

## ⚙️ Installation

### Local development

```bash
uv sync
uv run sm-tracker help
```

### Install as a CLI tool

```bash
uv pip install -e .
sm-tracker help
```

## 🚀 Quickstart

After `uv pip install -e .`, run:

1. Create credentials and app config via guided setup:

```bash
sm-tracker config
```

1. Track a snapshot:

```bash
sm-tracker track -p twitter -p bluesky
```

1. Show latest values with deltas:

```bash
sm-tracker show -p twitter -p bluesky
```

1. Inspect historical data:

```bash
sm-tracker history -p twitter --limit 10
```

## 🧭 Onboarding Guide

Use this flow for a clean checkout to first successful snapshot.

### 📦 1) Install dependencies

```bash
uv sync
```

### 🛠️ 2) Run guided setup

```bash
uv run sm-tracker config
```

The command will create or update:

- `.env` for API credentials and account identifiers
- `config.toml` for database path, log path, retention, and log level

### 🔑 3) Platform credential checklist

You can configure one or many platforms. Missing credentials skip only that platform.

#### Twitter/X

- `TWITTER_BEARER_TOKEN`
- `TWITTER_HANDLE`

#### Bluesky

- `BLUESKY_HANDLE`
- Optional: `BLUESKY_APP_PASSWORD`

#### Farcaster

- `FARCASTER_API_KEY`
- `FARCASTER_USERNAME`

Get API credentials from `https://warpcast.com/developer`.

#### Mastodon

- `MASTODON_ACCESS_TOKEN`
- `MASTODON_INSTANCE` (for example `mastodon.social`)

#### Threads

- `THREADS_ACCESS_TOKEN`
- `THREADS_USER_ID`
- Optional for OAuth flow: `THREADS_APP_ID`, `THREADS_APP_SECRET`, `THREADS_REDIRECT_URI`

Refresh Threads credentials via OAuth when needed:

```bash
uv run sm-tracker auth -p threads
```

#### Facebook

Option 1: Direct Page Token (Recommended)

- `FACEBOOK_PAGE_ACCESS_TOKEN`

Option 2: Automatic Token Exchange

- `FACEBOOK_ACCESS_TOKEN` (User Access Token)
- `FACEBOOK_ID` (The numeric ID of the Page)

### 📁 4) File locations

- Database path: from `config.toml` (`[paths.<profile>].db`)
- Logs directory: from `config.toml` (`[paths.<profile>].logs`)
- Log file name: `sm-tracker.log`

### 🧪 5) Common troubleshooting

- No platforms detected in `track`:
    - Run `sm-tracker config` and ensure required platform env vars are present.
- `show` says no snapshots yet:
    - Run `sm-tracker track` first.
- Threads token warning:
    - Run `sm-tracker auth -p threads` to refresh and save token values.

## 🧰 Commands

- `track`: fetch counts from configured platforms and save a snapshot (`--json` / `--csv` for structured output)
- `show`: print latest snapshot with deltas from previous snapshot (`--json` / `--csv` supported)
- `history`: print history table (`Date | Platform | Followers | Following | Delta`) or structured output with `--json` / `--csv`
- `config`: guided setup and validation for `.env` and `config.toml`
- `auth`: run OAuth for supported platforms (currently `threads`)
- `help`: print CLI usage

## 📝 Configuration

- Credential template: [`.env.example`](.env.example)
- App config template: [`config.toml.example`](config.toml.example)
- Full config and env variable reference: [`CONFIG_REFERENCE.md`](CONFIG_REFERENCE.md)

## 📊 Example output

```text
twitter
  Followers: 132 (+10)
  Following: 178 (0)
```

```text
Date | Platform | Followers | Following | Delta
2026-02-25T10:30:00Z | twitter | 122 | 178 | N/A
2026-02-26T10:30:00Z | twitter | 132 | 178 | +10
```

## 💡 Notes

- Default output is plain text. Use `--json` or `--csv` on `track`, `show`, and `history` for structured output.
- Missing credentials for one platform do not stop other platforms from running.
- `show` and `history` print empty-state guidance if there is no stored data yet.

## 📄 License

MIT
