# sm-tracker

CLI to track follower and following counts across Twitter/X, Bluesky, Farcaster, Mastodon, and Threads.

## Commands

- `track` — Fetch and save counts from configured platforms
- `show` — Display latest snapshot with deltas
- `history` — View past snapshots
- `config` — Guided setup for `.env` credentials
- `help` — Command usage

## Example

```bash
sm-tracker track -p twitter -p bluesky
sm-tracker show -p twitter -p bluesky
```

## Requirements

- Python 3.12+
- Platform API credentials (configured via `.env`)

## License

MIT
