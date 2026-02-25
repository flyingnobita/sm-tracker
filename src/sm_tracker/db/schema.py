"""Database schema initialization."""

from __future__ import annotations

from libsql_client import ClientSync  # type: ignore[import-untyped]

SCHEMA_STATEMENTS: tuple[str, str] = (
    """
    CREATE TABLE IF NOT EXISTS snapshots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL DEFAULT (datetime('now'))
    );
    """,
    """
    CREATE TABLE IF NOT EXISTS counts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        snapshot_id INTEGER NOT NULL,
        platform TEXT NOT NULL,
        following_count INTEGER,
        follower_count INTEGER,
        FOREIGN KEY (snapshot_id) REFERENCES snapshots(id)
    );
    """,
)


def init_schema(client: ClientSync) -> None:
    """Create all required database tables if they do not exist."""
    for statement in SCHEMA_STATEMENTS:
        client.execute(statement)
