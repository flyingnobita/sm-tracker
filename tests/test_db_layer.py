"""Phase 3 database layer tests."""

from pathlib import Path

from sm_tracker.db import (
    connect,
    fetch_history,
    fetch_latest,
    init_schema,
    insert_count,
    insert_snapshot,
    to_database_url,
)


def test_to_database_url_for_path_and_url() -> None:
    assert to_database_url(Path("data.db")) == "file:data.db"
    assert to_database_url("file:data.db") == "file:data.db"


def test_schema_init_creates_required_tables(tmp_path: Path) -> None:
    with connect(tmp_path / "schema.db") as client:
        init_schema(client)
        table_names = {
            str(row["name"])
            for row in client.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name IN ('snapshots', 'counts')
                """
            ).rows
        }
        assert table_names == {"snapshots", "counts"}


def test_fetch_latest_and_history_empty_db(tmp_path: Path) -> None:
    with connect(tmp_path / "empty.db") as client:
        init_schema(client)
        assert fetch_latest(client) == []
        assert fetch_history(client) == []


def test_insert_and_fetch_latest_snapshot_counts(tmp_path: Path) -> None:
    with connect(tmp_path / "crud.db") as client:
        init_schema(client)
        snapshot_id = insert_snapshot(client, timestamp="2025-02-25T10:00:00")

        first_count_id = insert_count(
            client,
            snapshot_id=snapshot_id,
            platform="twitter",
            follower_count=100,
            following_count=50,
        )
        assert first_count_id > 0

        insert_count(
            client,
            snapshot_id=snapshot_id,
            platform="farcaster",
            follower_count=42,
            following_count=None,
        )

        latest = fetch_latest(client)
        assert [row.platform for row in latest] == ["farcaster", "twitter"]
        assert latest[0].snapshot_id == snapshot_id
        assert latest[0].follower_count == 42
        assert latest[0].following_count is None
        assert latest[1].follower_count == 100
        assert latest[1].following_count == 50


def test_fetch_latest_prefers_newest_snapshot_on_duplicate_timestamps(
    tmp_path: Path,
) -> None:
    with connect(tmp_path / "duplicate.db") as client:
        init_schema(client)
        first_snapshot_id = insert_snapshot(client, timestamp="2025-02-25T10:00:00")
        second_snapshot_id = insert_snapshot(client, timestamp="2025-02-25T10:00:00")

        insert_count(
            client,
            snapshot_id=first_snapshot_id,
            platform="twitter",
            follower_count=100,
            following_count=10,
        )
        insert_count(
            client,
            snapshot_id=second_snapshot_id,
            platform="twitter",
            follower_count=110,
            following_count=12,
        )

        latest = fetch_latest(client)
        assert len(latest) == 1
        assert latest[0].snapshot_id == second_snapshot_id
        assert latest[0].follower_count == 110


def test_fetch_history_returns_newest_first_and_respects_limit(tmp_path: Path) -> None:
    with connect(tmp_path / "history.db") as client:
        init_schema(client)
        older_snapshot_id = insert_snapshot(client, timestamp="2025-02-24T10:00:00")
        newer_snapshot_id = insert_snapshot(client, timestamp="2025-02-25T10:00:00")

        insert_count(
            client,
            snapshot_id=older_snapshot_id,
            platform="twitter",
            follower_count=100,
            following_count=10,
        )
        insert_count(
            client,
            snapshot_id=newer_snapshot_id,
            platform="twitter",
            follower_count=120,
            following_count=11,
        )
        insert_count(
            client,
            snapshot_id=newer_snapshot_id,
            platform="bluesky",
            follower_count=80,
            following_count=12,
        )

        history = fetch_history(client)
        assert [row.snapshot_id for row in history] == [
            newer_snapshot_id,
            newer_snapshot_id,
            older_snapshot_id,
        ]

        limited_history = fetch_history(client, limit=2)
        assert len(limited_history) == 2
