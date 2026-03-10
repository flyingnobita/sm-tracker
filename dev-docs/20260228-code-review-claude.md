# Codebase Review: sm-tracker

Date: 2026-02-28

**Project:** Social media follower/following count tracker
**Version Reviewed:** 0.1.0 (historical pre-release review)
**Tech:** Python 3.12+, Typer CLI, libSQL, 8 platform adapters

---

## Overview

Well-structured MVP with good separation of concerns (CLI / config / db / adapters / logging). Modular adapter pattern, strong type annotations, and solid tooling (ruff, mypy, pytest). Recent code review rounds already addressed the most obvious security and correctness issues. The findings below reflect what remains.

---

## Critical

**1. Facebook access token leaked in URL query parameter**
`src/sm_tracker/platforms/facebook.py:68`

```python
url = f"...me/accounts?limit=100&access_token={quote(user_token)}"
```

The user access token is sent as a URL query parameter in `_fetch_page_token`. Query params appear in server access logs, browser history, proxy logs, and HTTP Referer headers. The Authorization header should be used instead (as is correctly done in `_build_request` and `create_facebook_adapter`'s fast-path at line 103).

---

## High

**2. `extract_int` exits early on the first key that fails coercion**
`src/sm_tracker/platforms/utils.py:20-24`

```python
if value is not None:
    try:
        return int(value)
    except (ValueError, TypeError):
        return None   # <-- bails instead of continuing to next key
```

If a key exists but its value is non-numeric (e.g., `"N/A"`), the function returns `None` immediately rather than falling through to the next candidate key. For example, `extract_int(data, "follower_count", "followerCount")` would return `None` even if `followerCount` holds a valid integer. The `return None` in the except block should be `continue`.

**3. Sensitive credentials stored in `repr`-visible dataclass fields**
Multiple adapter files (facebook.py:21, farcaster.py:21, twitter.py, mastodon.py, threads.py, instagram.py, youtube.py)

All adapters store tokens as plain dataclass fields without `field(repr=False)`. If any adapter object is ever `repr()`-ed (e.g., in an unhandled exception traceback or debug log), credentials are exposed. Each credential field should use `dataclasses.field(default=..., repr=False)`.

**4. `show` and `history` commands don't wrap `init_schema` in try-except**
`src/sm_tracker/cli/__init__.py:291, 365`

`track` correctly wraps `init_schema` in a try-except (lines 197-203), but `show` and `history` call it unguarded. A database error during schema init in these commands raises an unhandled exception.

**5. `instagram` and `youtube` missing from `_validate_required_env_values`**
`src/sm_tracker/cli/__init__.py:799-806`

The `missing_by_platform` dict in `_validate_required_env_values` includes 6 platforms but omits `instagram` and `youtube`. Running `sm-tracker config` will not warn users about missing Instagram/YouTube credentials.

---

## Medium

**6. `auth_command` over-requests OAuth scopes**
`src/sm_tracker/cli/__init__.py:466-473`

`CONTENT_PUBLISH`, `READ_REPLIES`, and `MANAGE_REPLIES` scopes are requested during Threads OAuth but are unnecessary for follower tracking. Only `BASIC` and `MANAGE_INSIGHTS` are used. This violates the principle of least privilege.

**7. `setup_logging` adds duplicate handlers on repeated calls**
`src/sm_tracker/logging/__init__.py`

If `_try_setup_logging()` is called more than once (possible in tests, or if the root callback fires multiple times), additional handlers get appended to the logger, causing duplicate log lines. A guard checking `if logger.handlers` should be added before attaching new handlers.

**8. `_read_existing_profile_settings` duplicates config-parsing logic**
`src/sm_tracker/cli/__init__.py:753-783`

This function re-implements TOML loading and profile/path/logging resolution that already exists in `src/sm_tracker/config/__init__.py`. The duplication means both need updating when config schema changes. It could be simplified by calling `load_config()` inside a try-except and reading the returned `AppConfig`.

**9. `_format_rows_csv` uses inconsistent column header for timestamp**
`src/sm_tracker/cli/__init__.py:621-627`

The header column is `"timestamp"` in history mode but `"snapshot_timestamp"` in show mode. Both modes actually output `row["snapshot_timestamp"]` for the value. Consumers of the CSV output can't rely on a stable schema. Standardize to one name.

**10. `history` JSON/CSV output always sets `following_delta` to `None`**
`src/sm_tracker/cli/__init__.py:582`

`_history_rows_with_deltas` hardcodes `"following_delta": None`. The structured output schema is then inconsistent with `show` output which computes both deltas. Either compute following deltas in history too, or document and name this field intentionally (e.g., `"following_delta_unsupported": null`).

**11. HTTP requests made inside factory function**
`src/sm_tracker/platforms/facebook.py:100-112`

`create_facebook_adapter` makes live HTTP requests to resolve the target ID when `FACEBOOK_ID` is absent. Factories should be pure constructors - network I/O belongs in `fetch_counts`. This also means tests require mocking `urlopen` even just to instantiate the adapter.

**12. `find_config_file` ignores `XDG_CONFIG_HOME`**
`src/sm_tracker/config/__init__.py:63-74`

The user config fallback hardcodes `~/.config/sm-tracker/config.toml` but doesn't respect the `XDG_CONFIG_HOME` environment variable. On systems where `XDG_CONFIG_HOME` is customized, the config file won't be found.

---

## Low

**13. `_warn_threads_token_expiry_if_needed` creates unnecessary `set()`**
`src/sm_tracker/cli/__init__.py:896`

```python
if "threads" not in set(selected_platforms):
```

`selected_platforms` is a `Sequence` and already supports `in` natively. The `set()` conversion is unnecessary overhead.

**14. Stale backward-compatibility fallback for `FARCASTER_MNEMONIC`**
`src/sm_tracker/platforms/farcaster.py:60-61`

The `FARCASTER_MNEMONIC` fallback was retained for compatibility with older configs. At some point this should be removed with a deprecation notice to users.

**15. `_fetch_history_sql` string concatenation produces trailing whitespace**
`src/sm_tracker/db/queries.py:118`

```python
_FETCH_HISTORY_SQL_LIMITED = _FETCH_HISTORY_SQL + " LIMIT ?"
```

`_FETCH_HISTORY_SQL` ends with a newline, so the `LIMIT ?` appends after whitespace. Harmless to SQLite but slightly messy.

**16. `_run_env_wizard` required/optional handling is redundant**
`src/sm_tracker/cli/__init__.py:692-698`

```python
if required:
    updated.pop(key, None)
    continue
updated.pop(key, None)  # same operation for optional
```

Both branches do the same thing. The `if required:` branch with `continue` is dead logic.

**17. Facebook Graph API version hardcoded**
`src/sm_tracker/platforms/facebook.py:28, 68, 103`

`v19.0` is hardcoded in three separate URL strings. As Facebook deprecates old versions, all three must be updated. Extracting to a module-level constant would make future updates a single-line change.

---

## Summary Table

| #   | Severity | File                  | Issue                                               |
| --- | -------- | --------------------- | --------------------------------------------------- |
| 1   | Critical | facebook.py:68        | Access token in URL query parameter                 |
| 2   | High     | utils.py:20-24        | `extract_int` early-exits on first coercion failure |
| 3   | High     | all adapters          | Credentials in `repr`-visible dataclass fields      |
| 4   | High     | cli:291, 365          | `init_schema` unguarded in `show`/`history`         |
| 5   | High     | cli:799-806           | Instagram/YouTube missing from env validation       |
| 6   | Medium   | cli:466-473           | Threads OAuth over-requests scopes                  |
| 7   | Medium   | logging/**init**.py   | Duplicate handlers on repeated `setup_logging`      |
| 8   | Medium   | cli:753-783           | Duplicated config-parsing logic                     |
| 9   | Medium   | cli:621-627           | Inconsistent CSV timestamp column name              |
| 10  | Medium   | cli:582               | `following_delta` always `None` in history output   |
| 11  | Medium   | facebook.py:100-112   | Network I/O in factory function                     |
| 12  | Medium   | config:63-74          | `XDG_CONFIG_HOME` not respected                     |
| 13  | Low      | cli:896               | Unnecessary `set()` for membership check            |
| 14  | Low      | farcaster.py:60-61    | Stale `FARCASTER_MNEMONIC` fallback                 |
| 15  | Low      | queries.py:118        | SQL string has trailing whitespace before LIMIT     |
| 16  | Low      | cli:692-698           | Redundant required/optional branch in env wizard    |
| 17  | Low      | facebook.py:28,68,103 | API version hardcoded in three places               |
