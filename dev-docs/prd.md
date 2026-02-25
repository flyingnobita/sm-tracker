# Social Media Tracker CLI (sm-tracker)

### TL;DR

A command-line tool (`sm-tracker`) for technical users to monitor follower and following counts across multiple major social media platforms: Twitter/X, Bluesky, Farcaster, Mastodon, and Threads. Built for developers, automation engineers, power users, and LLM agents, it offers plain-text reporting, historical delta comparisons, and robust local persistence. It is open-source, CLI-first, and engineered for workflow and automation integration, with a focus on extensibility and transparency.

---

## Goals

### Business Goals

- Release an open-source MVP for multi-platform social media tracking within four weeks.

- Reach at least 100 GitHub stars within two months for project visibility.

- Build an extensible foundation for fast contributor onboarding and rapid feature addition post-launch.

- Target integration with AI agents, developer automation, and scripting workflows.

### User Goals

- Allow users to easily monitor and compare follower/following counts across Twitter/X, Bluesky, Farcaster, Mastodon, and Threads from the CLI.

- Enable automated scheduled tracking and plain-text reporting for downstream automation and scripting.

- Provide historical tracking and "delta" displays for day-to-day trends.

- Minimize setup and dependency friction with simple, local configuration and clear onboarding.

- Support single-account per platform tracking (multi-account deferred post-MVP).

### Non-Goals

- No multi-account support in MVP.

- No graphical user interface or mobile support (CLI-only).

- No machine-readable data output (e.g. JSON, CSV) for MVP—plain-text output only.

---

## User Stories

**Technical User (Standalone)**

- As a power user, I want to check and track my follower and following counts for Twitter/X, Mastodon, Bluesky, Farcaster, and Threads from the command line, so I can understand my audience trends while scripting or working in the terminal.

- As a CLI user, I want the ability to specify which platforms to track using flags, ensuring customized and repeatable workflows.

**Automation Engineer / LLM Agent**

- As an automation engineer, I want to schedule follower tracking across multiple platforms via cron, and consume plain-text results that can be processed or used as prompts for further automation.

- As an LLM agent, I want to invoke `sm-tracker` in pipelines without interactive prompts so the output is predictable and easily parsed.

**Open-Source Maintainer**

- As a maintainer, I want modular code and clear separation of commands and per-platform logic, so new platforms and features can be added by contributors with minimal onboarding.

---

## Functional Requirements

- **Command-Line Interface (**`sm-tracker`**)**
  - Core commands:
    - `track`: Fetch and save the latest follower/following counts from all specified platforms and store in a local libSQL (SQLite-compatible) database.

    - `show`: Display the latest saved snapshot for each selected platform, showing deltas versus the previous snapshot.

    - `history`: List the full history of previous tracked values per platform, supporting both `--platform` and `--limit` flags for granular queries.

    - `config`: Run a guided setup for required `.env` configuration; creates or validates the presence of `.env`, ensuring required API env vars are present for all tracked platforms.

    - `help`: Command usage details.

  - Uses repeatable, optional flags for platform selection, e.g.:
    - `sm-tracker track -p twitter -p mastodon`

    - `sm-tracker show -p threads`

    - `sm-tracker history -p bluesky --limit 10`

  - All arguments and actions are scriptable and strictly non-interactive (no prompts except for the guided `config` command).

- **Supported Platforms (from MVP)**
  - Twitter/X, Bluesky, Farcaster, Mastodon, Threads

  - Farcaster uses Warpcast direct API (farcaster-py archived; no count fields).

  - Threads requires `MANAGE_INSIGHTS` scope for follower count via `insights.get_user_insights()`.

  - (Platform support implemented as per-platform modules/classes in the codebase.)

- **Data Storage & Persistence**
  - All tracking data is persisted locally using libSQL (SQLite-compatible) for robustness, concurrency, and extensibility.

  - No restriction on history retention for follower data; indefinite tracking enabled by schema.

  - Log data (operation logs, errors) retained for 14 days **by default**, with the retention period configurable via the `LOG_RETENTION_DAYS` environment variable; logs are stored in a dedicated `logs/` directory with required daily rotation.

- **Configuration**
  - Credentials and all runtime configuration are managed via environment variables loaded from a `.env` file in the local directory (or from process env).

  - The `config` command provides a guided setup and validation for `.env`, prompting the user through required API credentials for all enabled platforms, and creates or updates the file with appropriate warnings for missing/invalid variables.

  - Defensive onboarding: If `.env` is missing or incomplete, tool warns which platforms are skipped in output/log, but continues for properly configured platforms.

  - After MVP, the config format may migrate to `~/.config/sm-tracker/config.toml` for richer management, but environment variables via `.env` and the guided setup are required for MVP.

- **Behavior & Flow**
  - `track` fetches and saves current counts ONLY; does not display the result.

  - `show` displays the latest saved snapshot for selected platforms, highlighting deltas versus last snapshot, in plain text.

  - `history` prints all (or the specified limit of) historical snapshots for specified platforms.

  - Output is strictly plain text; no ANSI colors, formatting toggles, or rich console features.

- **Error Handling**
  - If platform credentials are missing/invalid, log and warn for affected platforms; skip and continue processing others—never fail the entire batch.

  - API rate limit errors are logged and warned; tool continues running for other platforms.

  - All errors are reported in plain-text; robust but transparent handling for integration into automated or LLM-driven systems.

  - No interactive error recovery/prompts outside of `config`—failure cases are clear and non-blocking.

- **Logging**
  - All logs are **always** written to BOTH the file system (under `logs/`) and the console, with no optionality—this is required and not user-configurable in MVP.

  - Daily log rotation is required.

  - Log retention is set to 14 days by default and may be overridden by the `LOG_RETENTION_DAYS` environment variable.

  - Logging includes command executions, tracked actions, platform API successes/failures, missing configs, and all error traces as appropriate.

- **Dependency Management**
  - `mise` for package/tool management on this machine; `uv` for Python dependencies and tasks/env.

- **Project Structure & Tech Stack**
  - CLI entrypoint: `sm-tracker` (not `tracker`).

  - Source code follows a package-based, modular organization:
    - All source code resides under `src/sm_tracker/`
      - `src/sm_tracker/cli/` (CLI entry logic and command parser, Typer app)

      - `src/sm_tracker/platforms/` (modular adapters for each platform)

      - `src/sm_tracker/db/` (database layer and utilities)

      - `src/sm_tracker/config/` (configuration handler)

      - `src/sm_tracker/logging/` (logging setup and utilities)

      - `src/sm_tracker/__main__.py` (entry point for CLI execution)

      - Additional shared modules/utilities as needed

  - No top-level flat Python files for these modules; everything is package-based and organized as described.

---

## User Experience

### Onboarding & First-Run

- Users install `sm-tracker` per project and access it via command line.

- The first run or explicit `sm-tracker config` launches a **guided setup** that creates or validates the `.env` file in the working directory, walks the user through supplying required API keys/tokens for each desired platform, and ensures `.env` is ready for use.

- Clear CLI and readme guidance describe all required env vars per platform.

- Running `sm-tracker help` displays full CLI usage patterns, including:

  ```
  sm-tracker track -p twitter -p threads
  sm-tracker show -p mastodon
  sm-tracker history -p bluesky --limit 5
  ```

* All logs are written to both the console and to `logs/`, showing command results and any onboarding or config issues.

### Core Flows

- **Tracking New Data:**
  - `sm-tracker track -p <platform>` (e.g., `sm-tracker track -p twitter -p threads`)

  - Loads `.env`, validates credentials (skipping platforms without them), fetches current counts, saves in the database.

  - Output and logs show updated platforms, skipped (due to missing config), and success/failure for each.

- **Viewing Latest Snapshot:**
  - `sm-tracker show -p <platform>` (e.g., `sm-tracker show -p farcaster`)

  - Reads latest and previous records, outputs a plain-text delta display, e.g.:

    ```
    Mastodon (@user@instance)
    Followers: 1,050 (+10)
    Following: 178 (0)
    Date: 2024-06-12 08:30
    ```

  - Delta format: first snapshot `(N/A)`, positive `(+n)`, negative `(-n)`, zero `(0)`. Platforms with no following metric show `Following: N/A`.

* **Viewing History:**
  - `sm-tracker history -p <platform> --limit 15`

  - Prints plain-text table: `Date | Platform | Followers | Following | Delta` (up to limit). Same delta rules as `show` (N/A, +n, -n, 0). Platform with no following shows `N/A`.

* **Automation & Scripting:**
  - All features designed for non-interactive, batch, and LLM/automation use; all outputs are machine/LLM-readable.

### Error/Edge Cases

- Partial/incomplete config: platforms without credentials are reported as skipped (in both file and console log), not as errors.

- Platform API rate limit or transient error: logged and warned; tool continues processing other platforms.

- With no config or no data, runs are clean no-ops with plain notifications—no crashes.

- **Empty-state messages:** `track` with no platforms configured: "Add at least one platform via `sm-tracker config` or .env". `show` or `history` with no data: "No snapshots yet. Run `sm-tracker track` first." / "No history yet. Run `sm-tracker track` first."

- No color or enhanced formatting: output is always plain text.

---

## Narrative Example

Jordan, a developer managing multiple online identities, wants to keep track of their audience metrics across Twitter/X, Mastodon, Threads, Bluesky, and Farcaster. They install `sm-tracker` and use the `sm-tracker config` guided setup to create their `.env` file with all necessary API keys.

They schedule a daily cron job:

```
sm-tracker track -p twitter -p mastodon -p threads

```

Results and logs are saved to both the console and a daily log file. Each day, Jordan checks recent trends with:

```
sm-tracker show -p twitter -p threads
sm-tracker history -p mastodon --limit 10

```

Everything is plain text, ready for scripts or LLM pipelines, and historical data is fully preserved. If any API calls fail (e.g., bad credentials or rate limits), warnings appear in both the current console session and the archived logs. Nothing blocks the rest of Jordan’s workflow.

---

## Success Metrics

### User Metrics

- Unique users/stars on GitHub repository.

- Command usage tracked via opt-in anonymous local analytics.

- GitHub feedback/issue satisfaction (target: >90% positive post-launch).

### Business Metrics

- 100+ GitHub stars in first month.

- At least 5 unique contributor PRs within two months.

- Inclusion in notable CLI/workflow tool lists.

### Technical Metrics

- Command completion >98% (skipping/handling missing configs gracefully).

- <1% API/API credential error rate.

- Sub-3-second runtime for tracking across all platforms.

### Logging/Tracking Plan

- All command invocations and errors logged to `logs/` directory—with retention for 14 days (configurable by `LOG_RETENTION_DAYS` env var).

- Platform usage breakdown tracked (anonymous/local).

- No cloud/external transmission of user data in MVP.

---

## Technical and Engineering Details

### Stack & Architecture

**Runtime:** Python 3.12+ (minimum required by meta-threads-sdk)

Source Layout

- `src/sm_tracker/cli/` (main CLI and Typer app)

- `src/sm_tracker/platforms/` (per-platform adapters)

- `src/sm_tracker/db/` (database operations)

- `src/sm_tracker/config/` (env/config management)

- `src/sm_tracker/logging/` (logging setup and utilities)

- `src/sm_tracker/__main__.py` (CLI entrypoint)

**No use of flat module files (no** `cli.py`**,** `db.py`**, etc. at top-level). All features and logic organized by folder per domain.**

### Security & Privacy

- User data only ever stored locally; no cloud sync/transmission.

- `.env` and database fully managed on user’s system; documented processes for removing them.

- All logs local; no remote logging or analytics.

### Extensibility/Scalability

- Each platform’s logic in an isolated adapter, enabling straightforward addition of new platforms post-MVP.

- Database and config support positioned for multi-account and enhanced features.

### Potential Implementation Challenges

- Maintaining resilience to upstream platform API/auth changes.

- Ensuring robust log rotation and environment-driven retention.

- Defensive onboarding in all config and error workflows.

---

## Milestones & Sequencing

### Delivery Phases

1. **MVP Development (1 week)**

- CLI commands: track, show, history (with `--platform` and `--limit`), config (guided), and help.

- Platform adapters: Twitter/X, Bluesky, Farcaster, Mastodon, Threads.

- Database integration via libSQL.

- Env-based/guided config onboarding.

- Command-line flag parsing and help output.

- Unified logging to both file and console.

2. **Testing & Documentation (2–3 days)**

- Automated test suite (pytest), lint (ruff), type check (mypy); CI via GitHub Actions.

- Full README, onboarding instructions, and config setup guides.

- Working usage scenarios/examples for all platforms.

3. **Public Release & Feedback (2–3 days)**

- Launch on GitHub (with issues/PRs active).

- Rapid iteration on early feedback/bugs.

4. **Roadmap & Enhancements (1–2 days)**

- Design for multi-account support, structured data output, additional platform adapters.

**Total Estimate:** 2 Weeks

**Team Size:** 1–2 contributors (product + engineering)
