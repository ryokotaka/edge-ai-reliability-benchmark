from dashboard.app import build_dashboard_html, build_metric_cards


def test_build_metric_cards_from_summaries() -> None:
    cards = build_metric_cards(
        {
            "recovery": {
                "recovered_rows": 120,
                "baseline": {"recovery_loss": 120},
                "optimized": {"recovery_loss": 0},
            },
            "inference": {
                "float32_like": {"model_state_bytes": 48},
                "int8_quantized_like": {"model_state_bytes": 6, "f1": 0.96},
            },
            "sampling": {
                "fixed_1hz": {"sampled_count": 100},
                "adaptive": {"sampled_count": 80, "estimated_inference_reduction": 0.2},
            },
            "batching": {
                "commit_reduction": 90,
                "direct_per_row": {"commit_count": 100},
                "batched": {"commit_count": 10},
            },
            "filtering": {
                "detection_delay_samples": 1,
                "threshold_only": {"false_positive": 2},
                "hysteresis": {"false_positive": 0},
            },
        }
    )

    assert [card.title for card in cards] == [
        "Recovery loss",
        "Model state",
        "Inference work",
        "SQLite commits",
        "False positives",
    ]


def test_dashboard_html_reports_missing_summaries(tmp_path) -> None:
    html = build_dashboard_html(tmp_path)

    assert "No experiment summaries found" in html
    assert "python3 scripts/run_recovery_experiment.py" in html
