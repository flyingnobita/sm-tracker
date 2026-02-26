"""Query helpers for snapshots and counts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from libsql_client import ClientSync  # type: ignore[import-untyped]


@dataclass(frozen=True)
class Snapshot:
    """A persisted snapshot row."""

    id: int
    timestamp: str


@dataclass(frozen=True)
class CountRow:
    """A persisted count row joined with snapshot metadata."""

    snapshot_id: int
    timestamp: str
    platform: str
    follower_count: int | None
    following_count: int | None


def insert_snapshot(client: ClientSync, *, timestamp: str | None = None) -> int:
    """Insert a snapshot and return its ID."""
    if timestamp is None:
        result = client.execute("INSERT INTO snapshots DEFAULT VALUES")
    else:
        result = client.execute(
            "INSERT INTO snapshots (timestamp) VALUES (?)",
            [timestamp],
        )

    snapshot_id = cast(int | None, result.last_insert_rowid)
    if snapshot_id is None:
        raise RuntimeError("Snapshot insert did not return a row ID.")
    return snapshot_id


def insert_count(
    client: ClientSync,
    *,
    snapshot_id: int,
    platform: str,
    follower_count: int | None,
    following_count: int | None,
) -> int:
    """Insert platform counts for a snapshot and return row ID."""
    result = client.execute(
        """
        INSERT INTO counts (snapshot_id, platform, following_count, follower_count)
        VALUES (?, ?, ?, ?)
        """,
        [snapshot_id, platform, following_count, follower_count],
    )
    count_row_id = cast(int | None, result.last_insert_rowid)
    if count_row_id is None:
        raise RuntimeError("Count insert did not return a row ID.")
    return count_row_id


def fetch_latest(client: ClientSync) -> list[CountRow]:
    """Fetch all platform counts for the latest snapshot."""
    result = client.execute(
        """
        SELECT
            s.id AS snapshot_id,
            s.timestamp AS timestamp,
            c.platform AS platform,
            c.follower_count AS follower_count,
            c.following_count AS following_count
        FROM counts c
        INNER JOIN snapshots s ON s.id = c.snapshot_id
        WHERE c.snapshot_id = (
            SELECT id
            FROM snapshots
            ORDER BY timestamp DESC, id DESC
            LIMIT 1
        )
        ORDER BY c.platform ASC
        """
    )

    return [
        CountRow(
            snapshot_id=int(row["snapshot_id"]),
            timestamp=str(row["timestamp"]),
            platform=str(row["platform"]),
            follower_count=int(row["follower_count"])
            if row["follower_count"] is not None
            else None,
            following_count=int(row["following_count"])
            if row["following_count"] is not None
            else None,
        )
        for row in result.rows
    ]


_FETCH_HISTORY_SQL = """
    SELECT
        s.id AS snapshot_id,
        s.timestamp AS timestamp,
        c.platform AS platform,
        c.follower_count AS follower_count,
        c.following_count AS following_count
    FROM counts c
    INNER JOIN snapshots s ON s.id = c.snapshot_id
    ORDER BY s.timestamp DESC, s.id DESC, c.platform ASC
    """

_FETCH_HISTORY_SQL_LIMITED = _FETCH_HISTORY_SQL + " LIMIT ?"


def fetch_history(client: ClientSync, *, limit: int | None = None) -> list[CountRow]:
    """Fetch historical counts across snapshots, newest first."""
    if limit is not None:
        result = client.execute(_FETCH_HISTORY_SQL_LIMITED, [limit])
    else:
        result = client.execute(_FETCH_HISTORY_SQL)
    return [
        CountRow(
            snapshot_id=int(row["snapshot_id"]),
            timestamp=str(row["timestamp"]),
            platform=str(row["platform"]),
            follower_count=int(row["follower_count"])
            if row["follower_count"] is not None
            else None,
            following_count=int(row["following_count"])
            if row["following_count"] is not None
            else None,
        )
        for row in result.rows
    ]
