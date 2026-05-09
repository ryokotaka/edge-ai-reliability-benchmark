from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from edge_agent.inference import load_csv_rows
from edge_agent.model_artifact import run_model_artifact_experiment
from edge_agent.tiny_model import (
    DEFAULT_EPOCHS,
    DEFAULT_LEARNING_RATE,
    DEFAULT_POSITIVE_CLASS_WEIGHT,
    DEFAULT_PROBABILITY_THRESHOLD,
    DEFAULT_TRAIN_RATIO,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run v10 exported quantized tiny-model artifact experiment."
    )
    parser.add_argument("--csv-path", type=Path, default=Path("data/sample.csv"))
    parser.add_argument("--output-dir", type=Path, default=Path("data/model_artifact_experiment"))
    parser.add_argument(
        "--artifact-name",
        default="quantized_tiny_model.json",
        help="Model artifact filename inside the output directory.",
    )
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--epochs", type=int, default=DEFAULT_EPOCHS)
    parser.add_argument("--learning-rate", type=float, default=DEFAULT_LEARNING_RATE)
    parser.add_argument(
        "--positive-class-weight",
        type=float,
        default=DEFAULT_POSITIVE_CLASS_WEIGHT,
    )
    parser.add_argument(
        "--probability-threshold",
        type=float,
        default=DEFAULT_PROBABILITY_THRESHOLD,
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = args.output_dir / args.artifact_name
    result = run_model_artifact_experiment(
        load_csv_rows(args.csv_path),
        artifact_path=artifact_path,
        train_ratio=args.train_ratio,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        positive_class_weight=args.positive_class_weight,
        probability_threshold=args.probability_threshold,
    )
    output_path = args.output_dir / "summary.json"
    output_path.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps(result, indent=2, sort_keys=True))
    print(f"wrote_artifact={artifact_path}")
    print(f"wrote_summary={output_path}")


if __name__ == "__main__":
    main()
