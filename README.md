# sm-tracker

CLI to track follower and following counts across Twitter/X, Bluesky, Farcaster, Mastodon, and Threads.

## Commands

- `track` — Fetch and save counts from configured platforms
- `show` — Display latest snapshot with deltas
- `history` — View past snapshots
- `config` — Guided setup for `.env` (credentials) and `config.toml` (paths, retention)
- `help` — Command usage

## Example

```bash
sm-tracker track -p twitter -p bluesky
sm-tracker show -p twitter -p bluesky
```

## Requirements

- Python 3.12+
- Platform API credentials (`.env`); app config (paths, retention) in `config.toml`

## Farcaster Credential Setup

1. Go to the Warpcast developer portal: `https://warpcast.com/developer`
2. Log in with your Farcaster account.
3. Create a new API application.
4. Copy the API key.
5. Save credentials in `.env`:

```env
FARCASTER_API_KEY=your_api_key_here
FARCASTER_USERNAME=your_farcaster_username
```

## License

MIT
