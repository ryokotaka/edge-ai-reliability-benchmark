from edge_agent.inference import QuantizedAnomalyScorer, calibrate_stats
from edge_agent.sampling import adaptive_sampling_metrics, fixed_rate_sampling_metrics


def _row(seq: int, *, status: str = "ok", temperature: float = 22.0) -> dict[str, str]:
    fault_type = "noise" if status == "noisy" else "none"
    return {
        "seq": str(seq),
        "temperature_c": str(temperature),
        "humidity_pct": "50.0",
        "pressure_hpa": "1000.0",
        "status": status,
        "fault_type": fault_type,
    }


def test_adaptive_sampling_skips_stable_rows() -> None:
    rows = [_row(seq, temperature=22.0 + (seq % 3) * 0.1) for seq in range(40)]
    stats = calibrate_stats(rows, max_rows=20)
    scorer = QuantizedAnomalyScorer(stats, threshold=3.0)

    fixed = fixed_rate_sampling_metrics(rows, scorer)
    adaptive = adaptive_sampling_metrics(
        rows,
        scorer,
        stable_after=5,
        low_power_interval=2,
        anomaly_hold_samples=3,
    )

    assert fixed.sampled_count == fixed.evaluated_count
    assert adaptive.sampled_count < fixed.sampled_count
    assert adaptive.estimated_inference_reduction > 0


def test_adaptive_sampling_counts_skipped_anomalies_as_missed() -> None:
    rows = [_row(seq, temperature=22.0) for seq in range(12)]
    rows[6] = _row(6, status="noisy", temperature=45.0)
    stats = calibrate_stats(rows, max_rows=6)
    scorer = QuantizedAnomalyScorer(stats, threshold=3.0)

    adaptive = adaptive_sampling_metrics(
        rows,
        scorer,
        stable_after=2,
        low_power_interval=3,
        anomaly_hold_samples=0,
    )

    assert adaptive.true_anomaly_count == 1
    assert adaptive.missed_anomaly_count == 1
    assert adaptive.skipped_anomaly_count == 1
    assert adaptive.recall == 0.0
