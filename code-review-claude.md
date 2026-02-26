# Code Review: sm-tracker

26 issues found across all source files.

---

## Critical (3)

**1. Bearer token echoed to stdout** - `cli/__init__.py:372,381`
The `auth_command()` prints the full Threads access token via `typer.echo()`, exposing it in shell history and terminal logs.

```python
# Current - DANGEROUS
typer.echo(f"Long-lived token: {long_token.access_token}")
# Fix: remove or mask
typer.echo("Long-lived token saved to .env successfully.")
```

**2. Raw exception messages surfaced to user** - `cli/__init__.py:151`
`fetch failed ({exc})` leaks internal API error details to stdout. Log at `LOGGER.exception()` level and show a generic message instead.

**3. Silent partial snapshots on DB failure** - `cli/__init__.py:134-176`
`init_schema()` and `insert_snapshot()` are outside the try-except, so if the DB fails mid-transaction, `insert_count()` calls fail silently while the user sees success output.

---

## High (6)

**4. NameError on DB connection failure** - `db/connection.py:22-30`
If `create_client_sync()` raises, the `finally` block calls `client.close()` on an unbound name. Initialize `client = None` before the call and guard in `finally`.

**5. `_coerce_int()` crashes on non-numeric strings** - `platforms/twitter.py:76-79`
`int(value)` has no `ValueError` guard. Same pattern exists in all five adapters (`_extract_count`, `_extract_metric`). Wrap in try-except returning `None`.

**6. Dynamic SQL construction** - `db/queries.py:106-124`
`sql += " LIMIT ?"` builds SQL by string concatenation. Currently safe due to parameterized binding, but fragile. Prefer a fixed safe form.

**7. Bluesky `TypeError` used for control flow** - `platforms/bluesky.py:25-29`

```python
try:
    return client.get_profile(actor=self.handle)
except TypeError:
    return client.get_profile(self.handle)
```

Legitimate `TypeError`s from bad data are silently swallowed. Use library version detection instead.

**8. No LOGGER call when adapter init fails** - `platforms/__init__.py:46-83`
`AdapterConfigError` is only appended to a warnings list, never logged. Debugging credential issues requires guesswork.

**9. Threads adapter `_extract_count` returns `0` not `None`** - `platforms/threads.py:55-71`
All other adapters return `int | None`; Threads returns `int`, masking missing data as zero. The DB schema and delta logic expect `None` to mean "unavailable."

---

## Medium (7)

**10. Platform name validated too late** - `cli/__init__.py:83-109`
Invalid `--platform xyz` is not rejected until deep inside `resolve_adapters()`. Validate against `SUPPORTED_PLATFORM_NAMES` in `_selected_platforms()` and raise a `typer.BadParameter` early.

**11. `ConfigError` shows wrong message** - `cli/__init__.py:190-195`
A corrupted or wrong-profile config shows `"No snapshots yet. Run sm-tracker track first."` - misleading. Surface the actual `ConfigError` message.

**12. Custom `.env` parser re-implements python-dotenv** - `cli/__init__.py:593-604`
`_read_env_file()` splits on `=` manually and will mangle values containing `=` or quoted strings. Use `dotenv_values()` from the already-imported `python-dotenv`.

**13. No validation of `--limit` in function body** - `cli/__init__.py:240`
Typer's `min=1` guard is bypass-able in tests. Add an explicit guard in the function body as a defense-in-depth measure.

**14. Missing observability on env var lookups** - `platforms/__init__.py`
No debug logging for which env vars were found vs. missing during adapter construction, making CI failures hard to diagnose.

**15. `expires_at_utc.isoformat().replace("+00:00", "Z")` is fragile** - `cli/__init__.py:380`
If timezone info is missing, the replace is a no-op and output is inconsistent. Use `strftime("%Y-%m-%dT%H:%M:%SZ")` with an explicit UTC assumption.

**16. Magic string `"threads"` in auth guard** - `cli/__init__.py:324`
`if selected_platform != "threads"` should reference `SUPPORTED_PLATFORM_NAMES` or a dedicated constant, not a bare string literal.

---

## Low (10)

**17-21. Code duplication in extraction helpers** - All five adapters
Near-identical `_extract_count` / `_extract_metric` / `_coerce_int` functions. A shared `platforms/utils.py` with a generic `extract_int(data, *keys) -> int | None` would consolidate bug fixes.

**22-23. Unused `tmp_path` parameter in tests** - `test_phase6_twitter.py:67`, `test_phase6_mastodon.py:66`
`_ = tmp_path` - remove the parameter if it's unused.

**24. No docstrings on private extraction helpers**
The fallback-key logic in `_extract_count` helpers is non-obvious; a one-line docstring explaining the key priority would help.

**25. DB file permissions not restricted**
The database file should be created with mode `0o600`. No chmod call exists anywhere.

**26. Hardcoded user-facing strings**
Minor future concern if i18n is ever needed - all output strings are inline literals.

---

## Priority order for fixes

| Priority | Issues |
|---|---|
| Fix before next release | #1, #2, #3, #4, #5 |
| Fix in next sprint | #6, #7, #9, #10, #11, #12 |
| Polish / nice-to-have | #13-#26 |
