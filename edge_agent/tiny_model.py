from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from statistics import mean, pstdev
from typing import Iterable, Mapping, Sequence

from edge_agent.inference import (
    DEFAULT_THRESHOLD,
    FloatAnomalyScorer,
    InferenceResult,
    calibrate_stats,
    compute_detection_metrics,
    load_csv_rows,
    parse_float,
)


FEATURE_COLUMNS = ("temperature_c", "humidity_pct", "pressure_hpa", "latency_ms")
DEFAULT_TRAIN_RATIO = 0.7
DEFAULT_EPOCHS = 400
DEFAULT_LEARNING_RATE = 0.01
DEFAULT_POSITIVE_CLASS_WEIGHT = 20.0
DEFAULT_PROBABILITY_THRESHOLD = 0.5


@dataclass(frozen=True)
class FeatureNormalizer:
    means: dict[str, float]
    stddevs: dict[str, float]


@dataclass(frozen=True)
class FloatTinyModel:
    normalizer: FeatureNormalizer
    weights: list[float]
    bias: float
    threshold: float = DEFAULT_PROBABILITY_THRESHOLD
    mode: str = "learned_float_like"

    def predict(self, row: Mapping[str, object]) -> InferenceResult:
        start = time.perf_counter()
        probability = self.probability(row)
        latency_ms = (time.perf_counter() - start) * 1000
        return InferenceResult(
            seq=int(row["seq"]),
            mode=self.mode,
            score=probability,
            is_anomaly=probability >= self.threshold,
            ground_truth_anomaly=is_ground_truth_anomaly(row),
            latency_ms=latency_ms,
        )

    def probability(self, row: Mapping[str, object]) -> float:
        features = normalized_deviation_features(row, self.normalizer)
        logit = self.bias + sum(weight * value for weight, value in zip(self.weights, features))
        return sigmoid(logit)

    def state_size_bytes(self) -> int:
        # Means + stddevs + weights + bias, stored as float-like 64-bit values.
        return (len(FEATURE_COLUMNS) * 2 + len(self.weights) + 1) * 8


@dataclass(frozen=True)
class QuantizedTinyModel:
    quantized_means: dict[str, int]
    quantized_stddevs: dict[str, int]
    quantized_weights: list[int]
    quantized_bias: int
    value_scale: int
    feature_scale: int
    weight_scale: int
    threshold: float = DEFAULT_PROBABILITY_THRESHOLD
    mode: str = "learned_quantized_like"

    @classmethod
    def from_float_model(
        cls,
        model: FloatTinyModel,
        *,
        value_scale: int = 1000,
        feature_scale: int = 1000,
        weight_scale: int = 1000,
    ) -> QuantizedTinyModel:
        return cls(
            quantized_means={
                name: int(round(value * value_scale))
                for name, value in model.normalizer.means.items()
            },
            quantized_stddevs={
                name: max(1, int(round(value * value_scale)))
                for name, value in model.normalizer.stddevs.items()
            },
            quantized_weights=[int(round(weight * weight_scale)) for weight in model.weights],
            quantized_bias=int(round(model.bias * weight_scale)),
            value_scale=value_scale,
            feature_scale=feature_scale,
            weight_scale=weight_scale,
            threshold=model.threshold,
        )

    def predict(self, row: Mapping[str, object]) -> InferenceResult:
        start = time.perf_counter()
        probability = self.probability(row)
        latency_ms = (time.perf_counter() - start) * 1000
        return InferenceResult(
            seq=int(row["seq"]),
            mode=self.mode,
            score=probability,
            is_anomaly=probability >= self.threshold,
            ground_truth_anomaly=is_ground_truth_anomaly(row),
            latency_ms=latency_ms,
        )

    def probability(self, row: Mapping[str, object]) -> float:
        features = quantized_deviation_features(
            row,
            self.quantized_means,
            self.quantized_stddevs,
            value_scale=self.value_scale,
            feature_scale=self.feature_scale,
        )
        weighted_sum = sum(
            weight * value for weight, value in zip(self.quantized_weights, features)
        )
        logit = (
            weighted_sum / (self.weight_scale * self.feature_scale)
            + self.quantized_bias / self.weight_scale
        )
        return sigmoid(logit)

    def state_size_bytes(self) -> int:
        # Means/stddevs as int32, weights/bias as int16-like quantized values.
        return len(FEATURE_COLUMNS) * 2 * 4 + (len(self.quantized_weights) + 1) * 2


def is_ground_truth_anomaly(row: Mapping[str, object]) -> bool:
    return row.get("status") == "noisy" or row.get("fault_type") == "noise"


def usable_tiny_rows(rows: Iterable[Mapping[str, object]]) -> list[Mapping[str, object]]:
    return [
        row
        for row in rows
        if row.get("status") != "missing"
        and all(parse_float(row.get(column)) is not None for column in FEATURE_COLUMNS)
    ]


def split_train_test_rows(
    rows: Iterable[Mapping[str, object]],
    *,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
) -> tuple[list[Mapping[str, object]], list[Mapping[str, object]]]:
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1")
    materialized = sorted(usable_tiny_rows(rows), key=lambda row: int(row["seq"]))
    if len(materialized) < 2:
        raise ValueError("at least two usable rows are required")
    split_index = int(len(materialized) * train_ratio)
    split_index = min(max(1, split_index), len(materialized) - 1)
    return materialized[:split_index], materialized[split_index:]


def build_feature_normalizer(rows: Iterable[Mapping[str, object]]) -> FeatureNormalizer:
    normal_rows = [
        row
        for row in usable_tiny_rows(rows)
        if row.get("status") == "ok" and row.get("fault_type") == "none"
    ]
    if len(normal_rows) < 2:
        raise ValueError("at least two normal rows are required for feature normalization")

    means: dict[str, float] = {}
    stddevs: dict[str, float] = {}
    for column in FEATURE_COLUMNS:
        values = [float(parse_float(row[column])) for row in normal_rows]
        means[column] = mean(values)
        stddev = pstdev(values)
        stddevs[column] = stddev if stddev > 0 else 1.0

    return FeatureNormalizer(means=means, stddevs=stddevs)


def normalized_deviation_features(
    row: Mapping[str, object],
    normalizer: FeatureNormalizer,
) -> list[float]:
    features = []
    for column in FEATURE_COLUMNS:
        value = parse_float(row.get(column))
        if value is None:
            raise ValueError(f"missing feature value for {column}")
        features.append(abs(value - normalizer.means[column]) / normalizer.stddevs[column])
    return features


def quantized_deviation_features(
    row: Mapping[str, object],
    quantized_means: Mapping[str, int],
    quantized_stddevs: Mapping[str, int],
    *,
    value_scale: int,
    feature_scale: int,
) -> list[int]:
    features = []
    for column in FEATURE_COLUMNS:
        value = parse_float(row.get(column))
        if value is None:
            raise ValueError(f"missing feature value for {column}")
        quantized_value = int(round(value * value_scale))
        features.append(
            abs(quantized_value - quantized_means[column])
            * feature_scale
            // quantized_stddevs[column]
        )
    return features


def sigmoid(value: float) -> float:
    if value >= 0:
        exponent = math.exp(-value)
        return 1 / (1 + exponent)
    exponent = math.exp(value)
    return exponent / (1 + exponent)


def train_float_tiny_model(
    rows: Iterable[Mapping[str, object]],
    *,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    positive_class_weight: float = DEFAULT_POSITIVE_CLASS_WEIGHT,
    threshold: float = DEFAULT_PROBABILITY_THRESHOLD,
) -> FloatTinyModel:
    if epochs <= 0:
        raise ValueError("epochs must be positive")
    if learning_rate <= 0:
        raise ValueError("learning_rate must be positive")
    if positive_class_weight <= 0:
        raise ValueError("positive_class_weight must be positive")

    materialized = sorted(usable_tiny_rows(rows), key=lambda row: int(row["seq"]))
    normalizer = build_feature_normalizer(materialized)
    weights = [0.0 for _ in FEATURE_COLUMNS]
    bias = 0.0

    for _ in range(epochs):
        for row in materialized:
            features = normalized_deviation_features(row, normalizer)
            target = 1.0 if is_ground_truth_anomaly(row) else 0.0
            probability = sigmoid(bias + sum(w * x for w, x in zip(weights, features)))
            row_weight = positive_class_weight if target else 1.0
            error = (probability - target) * row_weight
            for index, feature in enumerate(features):
                weights[index] -= learning_rate * error * feature
            bias -= learning_rate * error

    return FloatTinyModel(
        normalizer=normalizer,
        weights=weights,
        bias=bias,
        threshold=threshold,
    )


def run_model(
    model: FloatTinyModel | QuantizedTinyModel,
    rows: Sequence[Mapping[str, object]],
) -> list[InferenceResult]:
    return [model.predict(row) for row in rows]


def run_tiny_model_comparison(
    rows: Iterable[Mapping[str, object]],
    *,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    statistical_threshold: float = DEFAULT_THRESHOLD,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    positive_class_weight: float = DEFAULT_POSITIVE_CLASS_WEIGHT,
    probability_threshold: float = DEFAULT_PROBABILITY_THRESHOLD,
) -> dict[str, object]:
    materialized = list(rows)
    train_rows, test_rows = split_train_test_rows(materialized, train_ratio=train_ratio)

    statistical_stats = calibrate_stats(train_rows, max_rows=len(train_rows))
    statistical_model = FloatAnomalyScorer(
        statistical_stats,
        threshold=statistical_threshold,
    )
    statistical_results = [statistical_model.predict(row) for row in test_rows]

    learned_float = train_float_tiny_model(
        train_rows,
        epochs=epochs,
        learning_rate=learning_rate,
        positive_class_weight=positive_class_weight,
        threshold=probability_threshold,
    )
    learned_quantized = QuantizedTinyModel.from_float_model(learned_float)

    learned_float_results = run_model(learned_float, test_rows)
    learned_quantized_results = run_model(learned_quantized, test_rows)

    return {
        "train_ratio": train_ratio,
        "train_count": len(train_rows),
        "test_count": len(test_rows),
        "feature_columns": list(FEATURE_COLUMNS),
        "label_rule": "status = noisy or fault_type = noise",
        "statistical_threshold": statistical_threshold,
        "epochs": epochs,
        "learning_rate": learning_rate,
        "positive_class_weight": positive_class_weight,
        "probability_threshold": probability_threshold,
        "statistical_scorer": asdict(
            compute_detection_metrics(
                statistical_results,
                model_state_bytes=statistical_model.state_size_bytes(),
            )
        ),
        "learned_float_like": asdict(
            compute_detection_metrics(
                learned_float_results,
                model_state_bytes=learned_float.state_size_bytes(),
            )
        ),
        "learned_quantized_like": asdict(
            compute_detection_metrics(
                learned_quantized_results,
                model_state_bytes=learned_quantized.state_size_bytes(),
            )
        ),
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compare statistical scoring with a tiny learned sensor model."
    )
    parser.add_argument("csv_path", type=Path, nargs="?", default=Path("data/sample.csv"))
    parser.add_argument("--train-ratio", type=float, default=DEFAULT_TRAIN_RATIO)
    parser.add_argument("--statistical-threshold", type=float, default=DEFAULT_THRESHOLD)
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
    result = run_tiny_model_comparison(
        load_csv_rows(args.csv_path),
        train_ratio=args.train_ratio,
        statistical_threshold=args.statistical_threshold,
        epochs=args.epochs,
        learning_rate=args.learning_rate,
        positive_class_weight=args.positive_class_weight,
        probability_threshold=args.probability_threshold,
    )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
