from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Iterable, Mapping, Sequence

from edge_agent.inference import compute_detection_metrics
from edge_agent.tiny_model import (
    DEFAULT_EPOCHS,
    DEFAULT_LEARNING_RATE,
    DEFAULT_POSITIVE_CLASS_WEIGHT,
    DEFAULT_PROBABILITY_THRESHOLD,
    DEFAULT_TRAIN_RATIO,
    FEATURE_COLUMNS,
    QuantizedTinyModel,
    run_model,
    split_train_test_rows,
    train_float_tiny_model,
)


MODEL_ARTIFACT_VERSION = 1
MODEL_TYPE = "quantized_tiny_sensor_model"
LABEL_RULE = "status = noisy or fault_type = noise"


def quantized_tiny_model_to_artifact(
    model: QuantizedTinyModel,
    *,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    return {
        "artifact_version": MODEL_ARTIFACT_VERSION,
        "model_type": MODEL_TYPE,
        "feature_columns": list(FEATURE_COLUMNS),
        "label_rule": LABEL_RULE,
        "threshold": model.threshold,
        "value_scale": model.value_scale,
        "feature_scale": model.feature_scale,
        "weight_scale": model.weight_scale,
        "quantized_means": dict(model.quantized_means),
        "quantized_stddevs": dict(model.quantized_stddevs),
        "quantized_weights": list(model.quantized_weights),
        "quantized_bias": model.quantized_bias,
        "state_size_bytes": model.state_size_bytes(),
        "metadata": dict(metadata or {}),
    }


def quantized_tiny_model_from_artifact(
    artifact: Mapping[str, object],
) -> QuantizedTinyModel:
    if artifact.get("artifact_version") != MODEL_ARTIFACT_VERSION:
        raise ValueError("unsupported model artifact version")
    if artifact.get("model_type") != MODEL_TYPE:
        raise ValueError("unsupported model artifact type")
    if tuple(artifact.get("feature_columns", ())) != FEATURE_COLUMNS:
        raise ValueError("model artifact feature columns do not match this runtime")

    quantized_means = _int_mapping(artifact["quantized_means"])
    quantized_stddevs = _int_mapping(artifact["quantized_stddevs"])
    quantized_weights = [int(value) for value in artifact["quantized_weights"]]

    return QuantizedTinyModel(
        quantized_means=quantized_means,
        quantized_stddevs=quantized_stddevs,
        quantized_weights=quantized_weights,
        quantized_bias=int(artifact["quantized_bias"]),
        value_scale=int(artifact["value_scale"]),
        feature_scale=int(artifact["feature_scale"]),
        weight_scale=int(artifact["weight_scale"]),
        threshold=float(artifact["threshold"]),
    )


def export_quantized_tiny_model(
    model: QuantizedTinyModel,
    path: Path,
    *,
    metadata: Mapping[str, object] | None = None,
) -> dict[str, object]:
    artifact = quantized_tiny_model_to_artifact(model, metadata=metadata)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(artifact, indent=2, sort_keys=True) + "\n")
    return artifact


def load_quantized_tiny_model_artifact(path: Path) -> QuantizedTinyModel:
    return quantized_tiny_model_from_artifact(json.loads(path.read_text()))


def compare_model_predictions(
    left: QuantizedTinyModel,
    right: QuantizedTinyModel,
    rows: Sequence[Mapping[str, object]],
) -> dict[str, object]:
    left_results = run_model(left, rows)
    right_results = run_model(right, rows)
    mismatch_count = sum(
        1
        for left_result, right_result in zip(left_results, right_results)
        if left_result.is_anomaly != right_result.is_anomaly
    )
    max_probability_diff = max(
        (
            abs(left_result.score - right_result.score)
            for left_result, right_result in zip(left_results, right_results)
        ),
        default=0.0,
    )
    return {
        "prediction_mismatch_count": mismatch_count,
        "probability_max_abs_diff": max_probability_diff,
    }


def run_model_artifact_experiment(
    rows: Iterable[Mapping[str, object]],
    *,
    artifact_path: Path,
    train_ratio: float = DEFAULT_TRAIN_RATIO,
    epochs: int = DEFAULT_EPOCHS,
    learning_rate: float = DEFAULT_LEARNING_RATE,
    positive_class_weight: float = DEFAULT_POSITIVE_CLASS_WEIGHT,
    probability_threshold: float = DEFAULT_PROBABILITY_THRESHOLD,
) -> dict[str, object]:
    materialized = list(rows)
    train_rows, test_rows = split_train_test_rows(materialized, train_ratio=train_ratio)
    float_model = train_float_tiny_model(
        train_rows,
        epochs=epochs,
        learning_rate=learning_rate,
        positive_class_weight=positive_class_weight,
        threshold=probability_threshold,
    )
    quantized_model = QuantizedTinyModel.from_float_model(float_model)

    artifact = export_quantized_tiny_model(
        quantized_model,
        artifact_path,
        metadata={
            "train_ratio": train_ratio,
            "train_count": len(train_rows),
            "test_count": len(test_rows),
            "epochs": epochs,
            "learning_rate": learning_rate,
            "positive_class_weight": positive_class_weight,
            "probability_threshold": probability_threshold,
        },
    )
    loaded_model = load_quantized_tiny_model_artifact(artifact_path)

    in_memory_results = run_model(quantized_model, test_rows)
    loaded_results = run_model(loaded_model, test_rows)
    comparison = compare_model_predictions(quantized_model, loaded_model, test_rows)

    return {
        "artifact_path": str(artifact_path),
        "artifact_version": MODEL_ARTIFACT_VERSION,
        "model_type": MODEL_TYPE,
        "feature_columns": list(FEATURE_COLUMNS),
        "label_rule": LABEL_RULE,
        "train_ratio": train_ratio,
        "train_count": len(train_rows),
        "test_count": len(test_rows),
        "epochs": epochs,
        "learning_rate": learning_rate,
        "positive_class_weight": positive_class_weight,
        "probability_threshold": probability_threshold,
        "artifact_state_bytes": artifact["state_size_bytes"],
        "artifact_file_bytes": artifact_path.stat().st_size,
        "artifact_matches_in_memory": comparison["prediction_mismatch_count"] == 0
        and comparison["probability_max_abs_diff"] == 0.0,
        "prediction_mismatch_count": comparison["prediction_mismatch_count"],
        "probability_max_abs_diff": comparison["probability_max_abs_diff"],
        "in_memory_quantized_like": asdict(
            compute_detection_metrics(
                in_memory_results,
                model_state_bytes=quantized_model.state_size_bytes(),
            )
        ),
        "loaded_artifact": asdict(
            compute_detection_metrics(
                loaded_results,
                model_state_bytes=loaded_model.state_size_bytes(),
            )
        ),
    }


def _int_mapping(value: object) -> dict[str, int]:
    if not isinstance(value, Mapping):
        raise ValueError("expected mapping in model artifact")
    return {str(key): int(item) for key, item in value.items()}
