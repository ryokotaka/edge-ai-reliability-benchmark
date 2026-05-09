from edge_agent.tiny_model import (
    FEATURE_COLUMNS,
    QuantizedTinyModel,
    run_tiny_model_comparison,
    split_train_test_rows,
    train_float_tiny_model,
)


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


def test_tiny_model_training_is_deterministic() -> None:
    train_rows, _ = split_train_test_rows(_rows())

    first = train_float_tiny_model(train_rows, epochs=30)
    second = train_float_tiny_model(train_rows, epochs=30)

    assert first.weights == second.weights
    assert first.bias == second.bias


def test_float_tiny_model_detects_noisy_test_row() -> None:
    summary = run_tiny_model_comparison(_rows(), epochs=80)

    assert summary["feature_columns"] == list(FEATURE_COLUMNS)
    assert summary["learned_float_like"]["true_positive"] >= 1
    assert summary["learned_float_like"]["false_negative"] < summary["test_count"]


def test_quantized_tiny_model_uses_smaller_state() -> None:
    train_rows, _ = split_train_test_rows(_rows())
    float_model = train_float_tiny_model(train_rows, epochs=30)
    quantized_model = QuantizedTinyModel.from_float_model(float_model)

    assert quantized_model.state_size_bytes() < float_model.state_size_bytes()


def test_tiny_model_summary_contains_required_metric_keys() -> None:
    summary = run_tiny_model_comparison(_rows(), epochs=40)

    for section in ("statistical_scorer", "learned_float_like", "learned_quantized_like"):
        assert "precision" in summary[section]
        assert "recall" in summary[section]
        assert "f1" in summary[section]
        assert "false_positive" in summary[section]
        assert "false_negative" in summary[section]
        assert "p95_inference_latency_ms" in summary[section]
        assert "model_state_bytes" in summary[section]
