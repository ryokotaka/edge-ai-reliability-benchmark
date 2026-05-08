from __future__ import annotations

import argparse
import csv
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.buffer import LocalRecoveryBuffer
from edge_agent.metrics import compute_reliability_metrics, load_rows_from_sqlite
from edge_agent.storage import write_rows_to_sqlite


def load_csv_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="") as csv_file:
        return list(csv.DictReader(csv_file))


def _in_failure_window(row: dict[str, str], start: int, end: int) -> bool:
    seq = int(row["seq"])
    return start <= seq < end


def run_experiment(
    *,
    csv_path: Path,
    output_dir: Path,
    failure_start_seq: int,
    failure_length: int,
) -> dict[str, object]:
    rows = load_csv_rows(csv_path)
    expected_count = len(rows)
    failure_end_seq = failure_start_seq + failure_length

    output_dir.mkdir(parents=True, exist_ok=True)
    baseline_db = output_dir / "baseline_direct.sqlite"
    optimized_db = output_dir / "optimized_buffered.sqlite"
    buffer_path = output_dir / "pending_readings.jsonl"
    checkpoint_path = output_dir / "checkpoint.json"

    for path in (baseline_db, optimized_db, buffer_path, checkpoint_path):
        path.unlink(missing_ok=True)

    baseline_rows = [
        row for row in rows if not _in_failure_window(row, failure_start_seq, failure_end_seq)
    ]
    write_rows_to_sqlite(baseline_rows, baseline_db, replace=True)

    recovery_buffer = LocalRecoveryBuffer(buffer_path, checkpoint_path)
    optimized_direct_rows: list[dict[str, str]] = []
    for row in rows:
        if _in_failure_window(row, failure_start_seq, failure_end_seq):
            recovery_buffer.append(row)
        else:
            optimized_direct_rows.append(row)

    write_rows_to_sqlite(optimized_direct_rows, optimized_db, replace=True)
    recovered_rows = recovery_buffer.flush_to_sqlite(optimized_db)

    baseline_metrics = compute_reliability_metrics(
        load_rows_from_sqlite(baseline_db),
        expected_count=expected_count,
    )
    optimized_metrics = compute_reliability_metrics(
        load_rows_from_sqlite(optimized_db),
        expected_count=expected_count,
    )

    return {
        "expected_count": expected_count,
        "failure_start_seq": failure_start_seq,
        "failure_end_seq": failure_end_seq,
        "simulated_write_failure_rows": failure_length,
        "recovered_rows": recovered_rows,
        "baseline": asdict(baseline_metrics),
        "optimized": asdict(optimized_metrics),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare direct writes against local buffer/checkpoint recovery."
    )
    parser.add_argument("--csv-path", type=Path, default=Path("data/sample.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/recovery_experiment"))
    parser.add_argument("--failure-start-seq", type=int, default=600)
    parser.add_argument("--failure-length", type=int, default=120)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = run_experiment(
        csv_path=args.csv_path,
        output_dir=args.output_dir,
        failure_start_seq=args.failure_start_seq,
        failure_length=args.failure_length,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
