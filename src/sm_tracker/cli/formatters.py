"""Formatting helpers for CLI output."""

from __future__ import annotations

import csv
import json
from collections.abc import Mapping
from io import StringIO

from sm_tracker.db.queries import CountRow


def _format_delta(current: int | None, previous: int | None) -> str:
    if current is None or previous is None:
        return "N/A"

    delta = current - previous
    if delta > 0:
        return f"+{delta}"
    if delta < 0:
        return str(delta)
    return "0"


def _format_count_with_delta(value: int | None, delta: str) -> str:
    if value is None:
        return "N/A"
    return f"{value} ({delta})"


def _previous_rows_by_platform(
    history: list[CountRow], *, latest_snapshot_id: int
) -> dict[str, CountRow]:
    previous: dict[str, CountRow] = {}
    for row in history:
        if row.snapshot_id == latest_snapshot_id:
            continue
        previous.setdefault(row.platform, row)
    return previous


def _history_rows_with_deltas(
    rows: list[CountRow],
) -> list[dict[str, str | int | None]]:
    follower_deltas: list[str] = ["N/A"] * len(rows)
    following_deltas: list[str] = ["N/A"] * len(rows)
    indexes_by_platform: dict[str, list[int]] = {}

    for idx, row in enumerate(rows):
        indexes_by_platform.setdefault(row.platform, []).append(idx)

    for platform_indexes in indexes_by_platform.values():
        for pos, current_index in enumerate(platform_indexes):
            older_index = platform_indexes[pos + 1] if pos + 1 < len(platform_indexes) else None
            if older_index is not None:
                prev_follower = rows[older_index].follower_count
                prev_following = rows[older_index].following_count
            else:
                prev_follower = None
                prev_following = None

            follower_deltas[current_index] = _format_delta(
                rows[current_index].follower_count, prev_follower
            )
            following_deltas[current_index] = _format_delta(
                rows[current_index].following_count, prev_following
            )

    structured: list[dict[str, str | int | None]] = []
    for row, f_delta, fing_delta in zip(rows, follower_deltas, following_deltas, strict=False):
        structured.append(
            {
                "snapshot_id": row.snapshot_id,
                "snapshot_timestamp": row.timestamp,
                "platform": row.platform,
                "follower_count": row.follower_count,
                "following_count": row.following_count,
                "follower_delta": f_delta,
                "following_delta": fing_delta,
            }
        )
    return structured


def _show_rows_with_deltas(
    latest: list[CountRow], previous_by_platform: Mapping[str, CountRow]
) -> list[dict[str, str | int | None]]:
    rows: list[dict[str, str | int | None]] = []
    for row in latest:
        previous = previous_by_platform.get(row.platform)
        rows.append(
            {
                "snapshot_id": row.snapshot_id,
                "snapshot_timestamp": row.timestamp,
                "platform": row.platform,
                "follower_count": row.follower_count,
                "following_count": row.following_count,
                "follower_delta": _format_delta(
                    row.follower_count,
                    previous.follower_count if previous else None,
                ),
                "following_delta": _format_delta(
                    row.following_count,
                    previous.following_count if previous else None,
                ),
            }
        )
    return rows


def _format_rows_json(rows: list[dict[str, str | int | None]]) -> str:
    return json.dumps(rows)


def _format_rows_csv(rows: list[dict[str, str | int | None]], *, history_mode: bool = False) -> str:
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "snapshot_id",
            "timestamp",
            "platform",
            "follower_count",
            "following_count",
            "follower_delta",
            "following_delta",
        ]
    )
    for row in rows:
        writer.writerow(
            [
                row["snapshot_id"],
                row["snapshot_timestamp"],
                row["platform"],
                row["follower_count"] if row["follower_count"] is not None else "",
                row["following_count"] if row["following_count"] is not None else "",
                row["follower_delta"] if row["follower_delta"] is not None else "",
                row["following_delta"] if row["following_delta"] is not None else "",
            ]
        )
    return output.getvalue()
