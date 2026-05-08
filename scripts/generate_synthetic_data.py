from __future__ import annotations

import argparse
import csv
import random
from datetime import datetime, timedelta, timezone
from pathlib import Path


FIELDNAMES = [
    "ts_utc",
    "seq",
    "source",
    "temperature_c",
    "humidity_pct",
    "pressure_hpa",
    "latency_ms",
    "status",
    "fault_type",
]


def _rounded(value: float) -> str:
    return f"{value:.3f}"


def generate_rows(
    *,
    duration_minutes: int,
    frequency_hz: int,
    dropout_rate: float,
    jitter_rate: float,
    noisy_rate: float,
    restart_gap_rate: float,
    seed: int,
    start_time: datetime,
) -> list[dict[str, str]]:
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be positive")
    if frequency_hz <= 0:
        raise ValueError("frequency_hz must be positive")

    rng = random.Random(seed)
    expected_count = duration_minutes * 60 * frequency_hz
    step = timedelta(seconds=1 / frequency_hz)
    rows: list[dict[str, str]] = []

    for seq in range(expected_count):
        ts = start_time + (step * seq)
        status = "ok"
        fault_type = "none"

        event_roll = rng.random()
        if event_roll < dropout_rate:
            status = "missing"
            fault_type = "dropout"
        elif event_roll < dropout_rate + restart_gap_rate:
            status = "restart_gap"
            fault_type = "restart"
        elif event_roll < dropout_rate + restart_gap_rate + noisy_rate:
            status = "noisy"
            fault_type = "noise"

        if status == "missing":
            rows.append(
                {
                    "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                    "seq": str(seq),
                    "source": "synthetic",
                    "temperature_c": "",
                    "humidity_pct": "",
                    "pressure_hpa": "",
                    "latency_ms": "",
                    "status": status,
                    "fault_type": fault_type,
                }
            )
            continue

        latency_ms = rng.uniform(10, 80)
        if rng.random() < jitter_rate or status == "restart_gap":
            latency_ms = rng.uniform(100, 500)

        temperature_c = rng.uniform(20.0, 30.0)
        humidity_pct = rng.uniform(35.0, 75.0)
        pressure_hpa = rng.uniform(990.0, 1030.0)

        if status == "noisy":
            temperature_c += rng.choice([-1, 1]) * rng.uniform(8.0, 15.0)
            humidity_pct += rng.choice([-1, 1]) * rng.uniform(20.0, 30.0)
            pressure_hpa += rng.choice([-1, 1]) * rng.uniform(20.0, 40.0)

        rows.append(
            {
                "ts_utc": ts.isoformat().replace("+00:00", "Z"),
                "seq": str(seq),
                "source": "synthetic",
                "temperature_c": _rounded(temperature_c),
                "humidity_pct": _rounded(humidity_pct),
                "pressure_hpa": _rounded(pressure_hpa),
                "latency_ms": _rounded(latency_ms),
                "status": status,
                "fault_type": fault_type,
            }
        )

    return rows


def write_csv(rows: list[dict[str, str]], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", newline="") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Generate v0 synthetic sensor data.")
    parser.add_argument("--output", type=Path, default=Path("data/sample.csv"))
    parser.add_argument("--duration-minutes", type=int, default=30)
    parser.add_argument("--frequency-hz", type=int, default=1)
    parser.add_argument("--dropout-rate", type=float, default=0.03)
    parser.add_argument("--jitter-rate", type=float, default=0.05)
    parser.add_argument("--noisy-rate", type=float, default=0.01)
    parser.add_argument("--restart-gap-rate", type=float, default=0.005)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--start",
        default="2026-04-24T00:00:00Z",
        help="UTC start timestamp, for example 2026-04-24T00:00:00Z.",
    )
    return parser


def _parse_start(value: str) -> datetime:
    normalized = value.replace("Z", "+00:00")
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def main() -> None:
    args = _build_parser().parse_args()
    rows = generate_rows(
        duration_minutes=args.duration_minutes,
        frequency_hz=args.frequency_hz,
        dropout_rate=args.dropout_rate,
        jitter_rate=args.jitter_rate,
        noisy_rate=args.noisy_rate,
        restart_gap_rate=args.restart_gap_rate,
        seed=args.seed,
        start_time=_parse_start(args.start),
    )
    write_csv(rows, args.output)
    print(f"wrote_rows={len(rows)} output={args.output}")


if __name__ == "__main__":
    main()
