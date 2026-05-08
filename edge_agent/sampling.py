from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable, Mapping

from edge_agent.inference import (
    DEFAULT_THRESHOLD,
    QuantizedAnomalyScorer,
    calibrate_stats,
    load_csv_rows,
    run_scorer,
    usable_rows,
)


@dataclass(frozen=True)
class SamplingMetrics:
    mode: str
    evaluated_count: int
    sampled_count: int
    skipped_count: int
    sampling_ratio: float
    estimated_inference_reduction: float
    true_anomaly_count: int
    detected_anomaly_count: int
    missed_anomaly_count: int
    skipped_anomaly_count: int
    false_positive: int
    precision: float
    recall: float
    f1: float


def is_ground_truth_anomaly(row: Mapping[str, object]) -> bool:
    return row.get("status") == "noisy" or row.get("fault_type") == "noise"


def _f1(precision: float, recall: float) -> float:
    return (
        2 * precision * recall / (precision + recall)
        if precision + recall > 0
        else 0.0
    )


def fixed_rate_sampling_metrics(
    rows: Iterable[Mapping[str, object]],
    scorer: QuantizedAnomalyScorer,
) -> SamplingMetrics:
    materialized = usable_rows(rows)
    results = run_scorer(materialized, scorer)
    true_anomaly_count = sum(1 for row in materialized if is_ground_truth_anomaly(row))
    detected_anomaly_count = sum(
        1 for result in results if result.is_anomaly and result.ground_truth_anomaly
    )
    false_positive = sum(
        1 for result in results if result.is_anomaly and not result.ground_truth_anomaly
    )
    missed_anomaly_count = true_anomaly_count - detected_anomaly_count
    predicted_anomaly_count = detected_anomaly_count + false_positive
    precision = detected_anomaly_count / predicted_anomaly_count if predicted_anomaly_count else 0.0
    recall = detected_anomaly_count / true_anomaly_count if true_anomaly_count else 0.0

    return SamplingMetrics(
        mode="fixed_1hz",
        evaluated_count=len(materialized),
        sampled_count=len(materialized),
        skipped_count=0,
        sampling_ratio=1.0,
        estimated_inference_reduction=0.0,
        true_anomaly_count=true_anomaly_count,
        detected_anomaly_count=detected_anomaly_count,
        missed_anomaly_count=missed_anomaly_count,
        skipped_anomaly_count=0,
        false_positive=false_positive,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
    )


def adaptive_sampling_metrics(
    rows: Iterable[Mapping[str, object]],
    scorer: QuantizedAnomalyScorer,
    *,
    stable_after: int = 120,
    low_power_interval: int = 2,
    anomaly_hold_samples: int = 30,
) -> SamplingMetrics:
    if stable_after < 0:
        raise ValueError("stable_after must be non-negative")
    if low_power_interval < 1:
        raise ValueError("low_power_interval must be positive")
    if anomaly_hold_samples < 0:
        raise ValueError("anomaly_hold_samples must be non-negative")

    materialized = sorted(usable_rows(rows), key=lambda row: int(row["seq"]))
    sampled_results = []
    skipped_rows = []
    next_sample_seq = int(materialized[0]["seq"]) if materialized else 0
    stable_count = 0
    anomaly_hold_remaining = 0

    for row in materialized:
        seq = int(row["seq"])
        if seq < next_sample_seq:
            skipped_rows.append(row)
            continue

        result = scorer.predict(row)
        sampled_results.append(result)

        if result.is_anomaly:
            stable_count = 0
            anomaly_hold_remaining = anomaly_hold_samples
            next_interval = 1
        elif anomaly_hold_remaining > 0:
            anomaly_hold_remaining -= 1
            stable_count = 0
            next_interval = 1
        else:
            stable_count += 1
            next_interval = low_power_interval if stable_count >= stable_after else 1

        next_sample_seq = seq + next_interval

    true_anomaly_count = sum(1 for row in materialized if is_ground_truth_anomaly(row))
    detected_anomaly_count = sum(
        1 for result in sampled_results if result.is_anomaly and result.ground_truth_anomaly
    )
    false_positive = sum(
        1 for result in sampled_results if result.is_anomaly and not result.ground_truth_anomaly
    )
    skipped_anomaly_count = sum(1 for row in skipped_rows if is_ground_truth_anomaly(row))
    sampled_missed_anomaly_count = sum(
        1
        for result in sampled_results
        if not result.is_anomaly and result.ground_truth_anomaly
    )
    missed_anomaly_count = skipped_anomaly_count + sampled_missed_anomaly_count
    predicted_anomaly_count = detected_anomaly_count + false_positive
    precision = detected_anomaly_count / predicted_anomaly_count if predicted_anomaly_count else 0.0
    recall = detected_anomaly_count / true_anomaly_count if true_anomaly_count else 0.0
    sampling_ratio = len(sampled_results) / len(materialized) if materialized else 0.0

    return SamplingMetrics(
        mode="adaptive",
        evaluated_count=len(materialized),
        sampled_count=len(sampled_results),
        skipped_count=len(skipped_rows),
        sampling_ratio=sampling_ratio,
        estimated_inference_reduction=1.0 - sampling_ratio,
        true_anomaly_count=true_anomaly_count,
        detected_anomaly_count=detected_anomaly_count,
        missed_anomaly_count=missed_anomaly_count,
        skipped_anomaly_count=skipped_anomaly_count,
        false_positive=false_positive,
        precision=precision,
        recall=recall,
        f1=_f1(precision, recall),
    )


def run_sampling_comparison(
    rows: Iterable[Mapping[str, object]],
    *,
    threshold: float = DEFAULT_THRESHOLD,
    calibration_rows: int = 300,
    quantization_scale: int = 10,
    stable_after: int = 30,
    low_power_interval: int = 2,
    anomaly_hold_samples: int = 10,
) -> dict[str, object]:
    materialized = list(rows)
    stats = calibrate_stats(materialized, max_rows=calibration_rows)
    scorer = QuantizedAnomalyScorer(
        stats,
        threshold=threshold,
        scale=quantization_scale,
    )
    fixed_metrics = fixed_rate_sampling_metrics(materialized, scorer)
    adaptive_metrics = adaptive_sampling_metrics(
        materialized,
        scorer,
        stable_after=stable_after,
        low_power_interval=low_power_interval,
        anomaly_hold_samples=anomaly_hold_samples,
    )

    return {
        "threshold": threshold,
        "calibration_rows": calibration_rows,
        "quantization_scale": quantization_scale,
        "stable_after": stable_after,
        "low_power_interval": low_power_interval,
        "anomaly_hold_samples": anomaly_hold_samples,
        "fixed_1hz": asdict(fixed_metrics),
        "adaptive": asdict(adaptive_metrics),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare fixed-rate inference against adaptive sampling."
    )
    parser.add_argument("csv_path", type=Path, nargs="?", default=Path("data/sample.csv"))
    parser.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    parser.add_argument("--calibration-rows", type=int, default=300)
    parser.add_argument("--quantization-scale", type=int, default=10)
    parser.add_argument("--stable-after", type=int, default=120)
    parser.add_argument("--low-power-interval", type=int, default=2)
    parser.add_argument("--anomaly-hold-samples", type=int, default=30)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    result = run_sampling_comparison(
        load_csv_rows(args.csv_path),
        threshold=args.threshold,
        calibration_rows=args.calibration_rows,
        quantization_scale=args.quantization_scale,
        stable_after=args.stable_after,
        low_power_interval=args.low_power_interval,
        anomaly_hold_samples=args.anomaly_hold_samples,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
