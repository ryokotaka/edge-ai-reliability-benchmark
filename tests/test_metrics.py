from edge_agent.metrics import compute_reliability_metrics, nearest_rank_percentile


def test_nearest_rank_percentile_returns_95th_percentile_value() -> None:
    assert nearest_rank_percentile([10, 20, 30, 40, 50], 95) == 50


def test_compute_reliability_metrics_counts_missing_and_ok_rows() -> None:
    rows = [
        {"seq": 0, "latency_ms": 10.0, "status": "ok"},
        {"seq": 1, "latency_ms": "", "status": "missing"},
        {"seq": 2, "latency_ms": 50.0, "status": "ok"},
        {"seq": 3, "latency_ms": 100.0, "status": "noisy"},
        {"seq": 4, "latency_ms": 200.0, "status": "restart_gap"},
    ]

    metrics = compute_reliability_metrics(rows, expected_count=5)

    assert metrics.expected_count == 5
    assert metrics.observed_count == 5
    assert metrics.missing_count == 1
    assert metrics.ok_count == 2
    assert metrics.missing_rate == 0.2
    assert metrics.p95_latency_ms == 200.0
    assert metrics.uptime_ratio == 0.4

