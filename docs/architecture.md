# Architecture

This project is a small sensor-inference reliability benchmark for edge-AI-style
systems. The current implementation runs on a laptop with synthetic data, but the
pipeline is shaped so the same measurements can move to Raspberry Pi and real sensors
later.

## Current Pipeline

```text
synthetic sensor-like stream
  -> CSV sample
  -> SQLite readings table
  -> reliability metrics
  -> lightweight anomaly scoring
  -> tiny learned sensor model
  -> software optimization experiments
  -> summary JSON files
  -> static HTML dashboard
```

## Data Layer

`scripts/generate_synthetic_data.py` creates deterministic 1 Hz environmental readings:

- temperature
- humidity
- pressure
- latency jitter
- missing rows
- noisy rows
- restart-gap markers

`edge_agent/storage.py` loads the CSV into SQLite so the benchmark has a local storage
path similar to a small edge device.

## Measurement Layer

`edge_agent/metrics.py` calculates the base reliability metrics:

- `missing_rate`
- `p95_latency_ms`
- `uptime_ratio`
- `recovery_loss`

These metrics are intentionally simple. They make failure and recovery behavior visible
before the project adds real hardware noise.

## Experiment Layers

| Version | Experiment | Baseline | Optimized / alternate path |
| --- | --- | --- | --- |
| v1 | Local recovery | Direct SQLite write loses rows during simulated failure | JSONL buffer + checkpoint flushes rows after recovery |
| v2 | Lightweight inference | Float-like anomaly scoring | Quantized-like integer scoring |
| v3 | Sampling policy | Fixed 1 Hz inference | Adaptive sampling during stable periods |
| v4 | Storage writes | Per-row SQLite insert and commit | Batch insert and commit |
| v5 | Alert stability | Threshold-only alerting | 2-sample hysteresis confirmation |
| v6 | Result viewing | Markdown and JSON summaries | Local static dashboard |
| v7 | Tiny learned model | Statistical scorer and float learned classifier | Quantized-like learned classifier |

## Dashboard Layer

`dashboard/app.py` reads local summary files from `data/*_experiment/summary.json` and
writes `dashboard/index.html`.

The dashboard is only a viewing layer. It does not introduce a cloud backend, paid API,
JavaScript framework, or external data service.

## Intentional Boundaries

The current architecture avoids production-scale features so the benchmark stays
reproducible and easy to audit:

- no cloud service
- no remote database
- no private data source
- no camera input
- no external machine-learning framework
- no Kubernetes or distributed orchestration
- no hardware-performance claims until Raspberry Pi measurements exist
