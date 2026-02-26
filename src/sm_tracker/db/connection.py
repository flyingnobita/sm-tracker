"""libSQL connection management helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from libsql_client import ClientSync, create_client_sync  # type: ignore[import-untyped]


def to_database_url(path: str | Path) -> str:
    """Convert a file path or URL into a libSQL URL."""
    if isinstance(path, Path):
        path = str(path)

    if "://" in path or path.startswith("file:"):
        return path
    return f"file:{path}"


def _restrict_file_permissions(path: str | Path) -> None:
    """Set local DB file permissions to owner-only (0o600)."""
    path_str = str(path)
    # Skip remote URLs (libsql://, http://, https://, etc.)
    if "://" in path_str and not path_str.startswith("file:"):
        return
    file_path = Path(path_str.removeprefix("file:"))
    if file_path.exists():
        file_path.chmod(0o600)


@contextmanager
def connect(path: str | Path, auth_token: str | None = None) -> Iterator[ClientSync]:
    """Yield a sync libSQL client and close it after use."""
    database_url = to_database_url(path)
    client: ClientSync | None = None
    try:
        client = create_client_sync(database_url, auth_token=auth_token)
        _restrict_file_permissions(path)
        yield client
    finally:
        if client is not None:
            client.close()
