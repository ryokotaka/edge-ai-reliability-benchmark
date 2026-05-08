from __future__ import annotations

import argparse
import csv
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS readings (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts_utc TEXT NOT NULL,
  seq INTEGER NOT NULL,
  source TEXT NOT NULL,
  temperature_c REAL,
  humidity_pct REAL,
  pressure_hpa REAL,
  latency_ms REAL,
  status TEXT NOT NULL,
  fault_type TEXT NOT NULL,
  created_at_utc TEXT NOT NULL
);
"""


INSERT_SQL = """
INSERT INTO readings (
  ts_utc,
  seq,
  source,
  temperature_c,
  humidity_pct,
  pressure_hpa,
  latency_ms,
  status,
  fault_type,
  created_at_utc
) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
"""


def init_db(conn: sqlite3.Connection, *, replace: bool = False) -> None:
    if replace:
        conn.execute("DROP TABLE IF EXISTS readings")
    conn.execute(SCHEMA_SQL)
    conn.commit()


def _optional_float(value: str) -> float | None:
    return None if value == "" else float(value)


def _row_from_csv(raw: dict[str, str], created_at_utc: str) -> tuple[object, ...]:
    return (
        raw["ts_utc"],
        int(raw["seq"]),
        raw["source"],
        _optional_float(raw["temperature_c"]),
        _optional_float(raw["humidity_pct"]),
        _optional_float(raw["pressure_hpa"]),
        _optional_float(raw["latency_ms"]),
        raw["status"],
        raw["fault_type"],
        created_at_utc,
    )


def import_csv_to_sqlite(csv_path: Path, db_path: Path, *, replace: bool = True) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    created_at_utc = datetime.now(timezone.utc).isoformat(timespec="seconds")

    with csv_path.open(newline="") as csv_file, sqlite3.connect(db_path) as conn:
        init_db(conn, replace=replace)
        reader = csv.DictReader(csv_file)
        rows = [_row_from_csv(raw, created_at_utc) for raw in reader]
        conn.executemany(INSERT_SQL, rows)
        conn.commit()
        return len(rows)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Import v0 readings CSV into SQLite.")
    parser.add_argument("csv_path", type=Path, help="Path to generated readings CSV.")
    parser.add_argument("db_path", type=Path, help="Output SQLite database path.")
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append into an existing readings table instead of replacing it.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    count = import_csv_to_sqlite(args.csv_path, args.db_path, replace=not args.append)
    print(f"imported_rows={count}")


if __name__ == "__main__":
    main()
