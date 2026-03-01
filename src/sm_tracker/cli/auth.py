"""Command to run OAuth authentication."""

from __future__ import annotations

import json
import os
import urllib.request
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import typer
from dotenv import load_dotenv
from threads import ThreadsClient
from threads.constants import Scope

from sm_tracker.cli.app import app

_AUTH_SUPPORTED_PLATFORMS: frozenset[str] = frozenset({"threads", "instagram", "facebook"})


@app.command(name="auth")
def auth_command(
    platform: str = typer.Option(
        ...,
        "--platform",
        "-p",
        help="Target platform for auth flow (currently: threads, instagram, facebook).",
    ),
) -> None:
    """Run platform OAuth flow and save credentials to .env."""
    selected_platform = platform.strip().lower()
    if selected_platform not in _AUTH_SUPPORTED_PLATFORMS:
        supported = ", ".join(sorted(_AUTH_SUPPORTED_PLATFORMS))
        typer.echo(f"Unsupported auth platform: {platform}")
        typer.echo(f"Currently supported: {supported}")
        raise typer.Exit(code=1)

    load_dotenv()
    env_path = Path(".env")

    if selected_platform == "threads":
        _run_threads_auth(env_path)
    elif selected_platform in ("instagram", "facebook"):
        _run_meta_auth(env_path, selected_platform)


def _run_threads_auth(env_path: Path) -> None:
    app_id = os.getenv("THREADS_APP_ID", "").strip()
    app_secret = os.getenv("THREADS_APP_SECRET", "").strip()
    redirect_uri = os.getenv("THREADS_REDIRECT_URI", "https://localhost/callback").strip()
    if not app_id or not app_secret:
        typer.echo(
            "Missing THREADS_APP_ID or THREADS_APP_SECRET in environment. "
            "Set them in your .env file."
        )
        raise typer.Exit(code=1)

    client = ThreadsClient(access_token="")
    try:
        auth_url = client.auth.get_authorization_url(
            client_id=app_id,
            redirect_uri=redirect_uri,
            scopes=[
                Scope.BASIC,
                Scope.MANAGE_INSIGHTS,
            ],
        )
        typer.echo(
            "Open this URL and authorize the app. "
            "You will be redirected to THREADS_REDIRECT_URI with a code."
        )
        typer.echo(f"Open this URL: {auth_url}")

        callback_url = typer.prompt("Paste the full callback URL").strip()
        code = _extract_threads_code_from_callback_url(callback_url)
        if not code:
            typer.echo("Could not extract authorization code from callback URL.")
            raise typer.Exit(code=1)

        short_token = client.auth.exchange_code(
            client_id=app_id,
            client_secret=app_secret,
            redirect_uri=redirect_uri,
            code=code,
        )
        typer.echo(f"User ID: {short_token.user_id}")

        long_token = client.auth.get_long_lived_token(
            client_secret=app_secret,
            short_lived_token=short_token.access_token,
        )
        expires_at_utc = datetime.now(UTC) + timedelta(seconds=int(long_token.expires_in))
        expires_at_iso = expires_at_utc.strftime("%Y-%m-%dT%H:%M:%SZ")
        typer.echo(f"Expires at (UTC): {expires_at_iso}")

        if not env_path.exists():
            typer.echo("Could not find .env in current working directory.")
            raise typer.Exit(code=1)

        _upsert_env_var(env_path, "THREADS_ACCESS_TOKEN", long_token.access_token)
        _upsert_env_var(env_path, "THREADS_USER_ID", str(short_token.user_id))
        _upsert_env_var(env_path, "THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", expires_at_iso)
        typer.echo("Saved THREADS_ACCESS_TOKEN, THREADS_USER_ID, and expiry time to .env")
    finally:
        client.close()


def _run_meta_auth(env_path: Path, platform: str) -> None:
    from dotenv import set_key

    if not env_path.exists():
        env_path.touch()

    # Initial load of variables from env
    app_id = os.getenv("META_APP_ID", "").strip()
    app_secret = os.getenv("META_APP_SECRET", "").strip()
    short_token = os.getenv("META_USER_TOKEN_SHORT_LIVED", "").strip()

    while True:
        if not app_id:
            app_id = typer.prompt("Enter your Meta App ID").strip()
            set_key(str(env_path), "META_APP_ID", app_id)

        if not app_secret:
            app_secret = typer.prompt("Enter your Meta App Secret", hide_input=True).strip()
            set_key(str(env_path), "META_APP_SECRET", app_secret)

        if not short_token:
            short_token = typer.prompt(
                "Enter your fresh Short-Lived User Token", hide_input=True
            ).strip()
            set_key(str(env_path), "META_USER_TOKEN_SHORT_LIVED", short_token)

        typer.echo("Exchanging for long-lived user token...")
        url_exchange = (
            f"https://graph.facebook.com/v19.0/oauth/access_token"
            f"?grant_type=fb_exchange_token&client_id={app_id}"
            f"&client_secret={app_secret}&fb_exchange_token={short_token}"
        )
        req_exchange = urllib.request.Request(url_exchange)

        try:
            with urllib.request.urlopen(req_exchange) as response:
                data = json.loads(response.read().decode())
                long_user_token = data.get("access_token")
                typer.echo("Got long-lived user token successfully.")
                break  # Exit the while loop on success
        except urllib.error.HTTPError as e:
            error_data = {}
            try:
                error_data = json.loads(e.read().decode())
            except json.JSONDecodeError:
                pass

            error_msg = error_data.get("error", {}).get("message", "Unknown error")
            typer.echo(f"Failed to get long-lived user token: HTTP Error {e.code}: {e.reason}")
            typer.echo(f"Details: {error_msg}")

            # Reset values to prompt again on next loop
            typer.echo("\nPlease provide new credentials:")
            app_id = ""
            app_secret = ""
            short_token = ""
        except Exception as e:
            typer.echo(f"An unexpected error occurred: {e}")
            raise typer.Exit(code=1) from e

    if platform == "instagram":
        set_key(str(env_path), "LONG_LIVED_USER_TOKEN", long_user_token)
        typer.echo("Saved LONG_LIVED_USER_TOKEN to .env")

    elif platform == "facebook":
        typer.echo("Fetching long-lived page tokens...")
        url_pages = f"https://graph.facebook.com/v19.0/me/accounts?access_token={long_user_token}"
        req_pages = urllib.request.Request(url_pages)
        try:
            with urllib.request.urlopen(req_pages) as response:
                pages_data = json.loads(response.read().decode())

                if pages_data.get("data") and len(pages_data["data"]) > 0:
                    long_page_token = pages_data["data"][0].get("access_token")
                    page_name = pages_data["data"][0].get("name")
                    typer.echo(f"Got long-lived page token for '{page_name}'.")
                    set_key(str(env_path), "FACEBOOK_PAGE_ACCESS_TOKEN", long_page_token)
                    typer.echo("Saved FACEBOOK_PAGE_ACCESS_TOKEN to .env")
                else:
                    typer.echo(
                        "No pages found for this user. "
                        "Make sure you granted 'pages_read_engagement' and 'pages_show_list'."
                    )
                    raise typer.Exit(code=1)
        except Exception as e:
            typer.echo(f"Failed to get page tokens: {e}")
            if hasattr(e, "read"):
                typer.echo(e.read().decode())
            raise typer.Exit(code=1) from e


def _extract_threads_code_from_callback_url(callback_url: str) -> str:
    url = callback_url.strip()
    if not url:
        return ""
    if url.endswith("#_"):
        url = url[:-2]

    parsed = urlparse(url)
    query = parse_qs(parsed.query)
    code = query.get("code", [""])[0].strip()
    if not code and "code=" in url:
        # Fallback for malformed callback URL input.
        code = url.split("code=", maxsplit=1)[1].strip()
    if code.endswith("#_"):
        code = code[:-2]
    return code


def warn_threads_token_expiry_if_needed(
    selected_platforms: Sequence[str],
    *,
    env: Mapping[str, str] | None = None,
    now_utc: datetime | None = None,
) -> None:
    if "threads" not in selected_platforms:
        return

    env_map = os.environ if env is None else env
    raw_expiry = env_map.get("THREADS_ACCESS_TOKEN_EXPIRES_AT_UTC", "").strip()
    if not raw_expiry:
        return

    try:
        normalized = raw_expiry
        if normalized.endswith("Z"):
            normalized = normalized[:-1] + "+00:00"
        expires_at = datetime.fromisoformat(normalized)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
        else:
            expires_at = expires_at.astimezone(UTC)
    except ValueError:
        typer.echo(
            "Threads access token expiry is invalid. "
            "Run `sm-tracker auth -p threads` to refresh it."
        )
        return

    current_time = datetime.now(UTC) if now_utc is None else now_utc
    if expires_at <= current_time:
        typer.echo(
            "Threads access token is expired. Run `sm-tracker auth -p threads` to refresh it."
        )
        return

    if expires_at <= current_time + timedelta(days=7):
        typer.echo(
            f"Threads access token expires soon ({expires_at.isoformat()}). "
            "Run `sm-tracker auth -p threads` to refresh it."
        )


def _upsert_env_var(env_path: Path, key: str, value: str) -> None:
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = False
    for idx, line in enumerate(lines):
        if line.startswith(f"{key}="):
            lines[idx] = f"{key}={value}"
            updated = True
            break
    if not updated:
        lines.append(f"{key}={value}")
    env_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
