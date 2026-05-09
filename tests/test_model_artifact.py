import json

from edge_agent.model_artifact import (
    MODEL_ARTIFACT_VERSION,
    MODEL_TYPE,
    compare_model_predictions,
    export_quantized_tiny_model,
    load_quantized_tiny_model_artifact,
    quantized_tiny_model_to_artifact,
    run_model_artifact_experiment,
)
from edge_agent.tiny_model import QuantizedTinyModel, split_train_test_rows, train_float_tiny_model


def _row(seq: int, *, noisy: bool = False) -> dict[str, str]:
    if noisy:
        return {
            "seq": str(seq),
            "temperature_c": "44.0" if seq % 2 == 0 else "6.0",
            "humidity_pct": "92.0" if seq % 2 == 0 else "14.0",
            "pressure_hpa": "1065.0" if seq % 2 == 0 else "940.0",
            "latency_ms": "220.0",
            "status": "noisy",
            "fault_type": "noise",
        }

    return {
        "seq": str(seq),
        "temperature_c": str(22.0 + (seq % 5) * 0.2),
        "humidity_pct": str(48.0 + (seq % 7) * 0.3),
        "pressure_hpa": str(1002.0 + (seq % 3) * 0.4),
        "latency_ms": str(28.0 + (seq % 4) * 1.5),
        "status": "ok",
        "fault_type": "none",
    }


def _rows() -> list[dict[str, str]]:
    noisy_sequences = {12, 36, 64, 72}
    return [_row(seq, noisy=seq in noisy_sequences) for seq in range(80)]


def _quantized_model() -> tuple[QuantizedTinyModel, list[dict[str, str]]]:
    train_rows, test_rows = split_train_test_rows(_rows())
    float_model = train_float_tiny_model(train_rows, epochs=80)
    return QuantizedTinyModel.from_float_model(float_model), test_rows


def test_quantized_artifact_contains_required_runtime_state() -> None:
    model, _ = _quantized_model()
    artifact = quantized_tiny_model_to_artifact(model)

    assert artifact["artifact_version"] == MODEL_ARTIFACT_VERSION
    assert artifact["model_type"] == MODEL_TYPE
    assert "quantized_means" in artifact
    assert "quantized_stddevs" in artifact
    assert "quantized_weights" in artifact
    assert "quantized_bias" in artifact
    assert artifact["state_size_bytes"] == model.state_size_bytes()


def test_quantized_artifact_round_trip_preserves_predictions(tmp_path) -> None:
    model, test_rows = _quantized_model()
    path = tmp_path / "quantized_tiny_model.json"
    export_quantized_tiny_model(model, path)
    loaded = load_quantized_tiny_model_artifact(path)

    comparison = compare_model_predictions(model, loaded, test_rows)

    assert comparison["prediction_mismatch_count"] == 0
    assert comparison["probability_max_abs_diff"] == 0.0


def test_model_artifact_experiment_writes_loadable_artifact(tmp_path) -> None:
    artifact_path = tmp_path / "artifact.json"
    summary = run_model_artifact_experiment(
        _rows(),
        artifact_path=artifact_path,
        epochs=80,
    )

    artifact = json.loads(artifact_path.read_text())

    assert artifact["artifact_version"] == MODEL_ARTIFACT_VERSION
    assert summary["artifact_matches_in_memory"] is True
    assert summary["prediction_mismatch_count"] == 0
    assert summary["loaded_artifact"]["true_positive"] >= 1


def test_model_artifact_summary_contains_required_metric_keys(tmp_path) -> None:
    summary = run_model_artifact_experiment(
        _rows(),
        artifact_path=tmp_path / "artifact.json",
        epochs=80,
    )

    for section in ("in_memory_quantized_like", "loaded_artifact"):
        assert "precision" in summary[section]
        assert "recall" in summary[section]
        assert "f1" in summary[section]
        assert "false_positive" in summary[section]
        assert "false_negative" in summary[section]
        assert "p95_inference_latency_ms" in summary[section]
        assert "model_state_bytes" in summary[section]
    assert "artifact_file_bytes" in summary
