from __future__ import annotations

import argparse
import json
import sqlite3
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping, Sequence


DEFAULT_EXPECTED_COUNT = 1800


@dataclass(frozen=True)
class ReliabilityMetrics:
    expected_count: int
    observed_count: int
    missing_count: int
    ok_count: int
    missing_rate: float
    p95_latency_ms: float | None
    uptime_ratio: float


def nearest_rank_percentile(values: Sequence[float], percentile: float) -> float | None:
    if not values:
        return None
    if not 0 < percentile <= 100:
        raise ValueError("percentile must be in the range (0, 100]")

    ordered = sorted(values)
    rank = max(1, int((percentile / 100) * len(ordered) + 0.999999999))
    return ordered[min(rank, len(ordered)) - 1]


def compute_reliability_metrics(
    rows: Iterable[Mapping[str, object]],
    expected_count: int = DEFAULT_EXPECTED_COUNT,
) -> ReliabilityMetrics:
    if expected_count <= 0:
        raise ValueError("expected_count must be positive")

    materialized = list(rows)
    missing_count = sum(1 for row in materialized if row.get("status") == "missing")
    ok_count = sum(1 for row in materialized if row.get("status") == "ok")

    latencies = [
        float(row["latency_ms"])
        for row in materialized
        if row.get("status") != "missing" and row.get("latency_ms") not in (None, "")
    ]

    return ReliabilityMetrics(
        expected_count=expected_count,
        observed_count=len(materialized),
        missing_count=missing_count,
        ok_count=ok_count,
        missing_rate=missing_count / expected_count,
        p95_latency_ms=nearest_rank_percentile(latencies, 95),
        uptime_ratio=ok_count / expected_count,
    )


def load_rows_from_sqlite(db_path: Path) -> list[dict[str, object]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """
            SELECT
              seq,
              source,
              temperature_c,
              humidity_pct,
              pressure_hpa,
              latency_ms,
              status,
              fault_type
            FROM readings
            ORDER BY seq
            """
        ).fetchall()
    return [dict(row) for row in rows]


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Compute v0 reliability metrics.")
    parser.add_argument("db_path", type=Path, help="Path to the SQLite readings database.")
    parser.add_argument(
        "--expected-count",
        type=int,
        default=DEFAULT_EXPECTED_COUNT,
        help="Expected number of samples. Defaults to 1800 for 30 minutes at 1 Hz.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    rows = load_rows_from_sqlite(args.db_path)
    metrics = compute_reliability_metrics(rows, expected_count=args.expected_count)
    print(json.dumps(asdict(metrics), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

