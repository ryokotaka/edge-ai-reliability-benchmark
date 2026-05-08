from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.inference import load_csv_rows
from edge_agent.sampling import run_sampling_comparison


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run v3 adaptive sampling comparison.")
    parser.add_argument("--csv-path", type=Path, default=Path("data/sample.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/sampling_experiment"))
    parser.add_argument("--threshold", type=float, default=3.0)
    parser.add_argument("--calibration-rows", type=int, default=300)
    parser.add_argument("--quantization-scale", type=int, default=10)
    parser.add_argument("--stable-after", type=int, default=120)
    parser.add_argument("--low-power-interval", type=int, default=2)
    parser.add_argument("--anomaly-hold-samples", type=int, default=30)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    result = run_sampling_comparison(
        load_csv_rows(args.csv_path),
        threshold=args.threshold,
        calibration_rows=args.calibration_rows,
        quantization_scale=args.quantization_scale,
        stable_after=args.stable_after,
        low_power_interval=args.low_power_interval,
        anomaly_hold_samples=args.anomaly_hold_samples,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
