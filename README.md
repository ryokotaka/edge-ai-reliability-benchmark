# Edge AI Reliability Benchmark

## Problem

AI inference systems often fail in ways that are hidden in clean benchmark settings:
sensor or simulation streams can be delayed, missing, noisy, or interrupted,
local storage can become a bottleneck, and lightweight inference can increase latency,
memory use, and recovery risk.

This project builds a small reproducible edge AI reliability benchmark to collect
sensor or simulation data, store it locally, run lightweight inference or anomaly
detection, measure reliability and inference cost, and compare software optimizations
under physical and resource-constrained conditions.

## What This System Does

This project is building a minimal edge AI reliability and optimization pipeline:

1. Generate or collect sensor-like data
2. Store readings locally in SQLite
3. Measure reliability metrics
4. Run lightweight anomaly detection
5. Apply software-level optimizations
6. Compare baseline vs optimized results
7. Explain results with reproducible logs and a dashboard

The current implementation covers synthetic data generation, SQLite storage,
reliability metrics, a local buffer / checkpoint recovery experiment, and a
lightweight anomaly scoring experiment that compares float-like and quantized-like
inference state. It also includes an adaptive sampling experiment that compares
fixed 1 Hz inference against lower-frequency stable-period sampling, plus a SQLite
batch-write experiment, a small hysteresis filter experiment for transient false
positives, and a local static HTML dashboard for comparing experiment summaries.

## Architecture

```text
synthetic sensor data
  -> collector / generator
  -> SQLite
  -> lightweight inference / anomaly detection
  -> metrics
  -> optimization
  -> dashboard
  -> experiment log
```

## Current Version

`v5` uses synthetic environmental sensor data instead of real hardware.
The goal is to make the reliability, recovery, lightweight inference, adaptive
sampling, storage-write, and false-positive filtering pipeline measurable before
adding Raspberry Pi hardware and real sensor constraints.

The base measurement flow is:

```text
synthetic sensor data
  -> CSV
  -> SQLite readings table
  -> reliability metrics
  -> README explanation
```

The first software optimization experiment is:

```text
synthetic sensor data
  -> simulated SQLite write failure
  -> baseline direct write loses rows
  -> optimized local JSONL buffer checkpoints rows
  -> recovered rows are flushed to SQLite
  -> baseline vs optimized recovery metrics
```

The second software optimization experiment is:

```text
SQLite / CSV readings
  -> calibrate normal environmental ranges
  -> float-like anomaly scoring
  -> quantized-like anomaly scoring
  -> compare detection quality, inference latency, and state size
```

The third software optimization experiment is:

```text
quantized-like anomaly scorer
  -> fixed 1 Hz inference baseline
  -> adaptive sampling during stable periods
  -> compare sampled rows, estimated inference reduction, recall, and F1
```

The fourth software optimization experiment is:

```text
CSV readings
  -> direct per-row SQLite writes
  -> batched SQLite writes
  -> compare insert calls, commit count, and elapsed write time
```

The fifth software optimization experiment is:

```text
synthetic transient spikes
  -> threshold-only anomaly alerts
  -> 2-sample hysteresis filter
  -> compare false positives, recall, F1, and detection delay
```

The local dashboard flow is:

```text
experiment summary JSON files
  -> dashboard/app.py
  -> dashboard/index.html
```

## Metrics

| Metric | Meaning |
| --- | --- |
| `missing_rate` | Fraction of expected samples that are missing |
| `p95_latency_ms` | 95th percentile of non-missing sample latency |
| `uptime_ratio` | Fraction of expected samples that are normal `ok` readings |
| `recovery_loss` | Expected sequence slots absent after a restart or write failure |
| `inference_latency_ms` | Time spent in lightweight anomaly detection |
| `memory_mb` | Approximate memory usage during inference |
| `false_positive` | Normal or transient rows incorrectly flagged as anomalies |
| `detection_delay_samples` | How many samples later an optimized alert is confirmed |

The v0 implementation calculates `missing_rate`, `p95_latency_ms`, and
`uptime_ratio`. The v1 recovery experiment also calculates `recovery_loss`.
The v2 inference experiment calculates precision, recall, F1, p95 inference
latency, and model state size. This is lightweight anomaly scoring, not a neural
network model yet. The v3 adaptive sampling experiment estimates inference-work
reduction and measures the detection-quality trade-off. The v4 batch-write experiment
measures SQLite write-call and commit-count reduction. The v5 stability-filter
experiment measures false-positive reduction against detection delay.

## Optimization Plan

The project does not stop at measurement. The final goal is to compare a baseline
pipeline against software-level optimizations.

| Problem | Optimization | Main Metrics |
| --- | --- | --- |
| missing samples or restart loss | local buffer / checkpoint | missing rate / recovery loss |
| storage latency | batch writes | p95 latency / write count |
| heavy inference | quantization / smaller model | inference latency / memory / accuracy drop |
| wasted work during normal periods | adaptive sampling | CPU / power / event detection quality |
| transient noisy spikes | hysteresis / smoothing | false positives / recall / detection delay |

The first planned optimization is local buffering and checkpoint recovery. The second
is quantized or smaller lightweight inference.

## Synthetic Data

The v0 simulator generates 30 minutes of 1 Hz sensor-like data with:

- temperature
- humidity
- pressure
- latency jitter
- synthetic dropout
- optional noisy readings
- optional restart-gap markers

The CSV schema is:

| Column | Type | Meaning |
| --- | --- | --- |
| `ts_utc` | text | Observation timestamp |
| `seq` | int | Expected sequence number |
| `source` | text | `synthetic` for v0 |
| `temperature_c` | float | Environmental temperature |
| `humidity_pct` | float | Environmental humidity |
| `pressure_hpa` | float | Environmental pressure |
| `latency_ms` | float | Acquisition latency |
| `status` | text | `ok`, `missing`, `noisy`, or `restart_gap` |
| `fault_type` | text | `none`, `dropout`, `noise`, or `restart` |

## Quick Start

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip pytest

python3 scripts/generate_synthetic_data.py
python3 -m edge_agent.storage data/sample.csv data/readings.sqlite
python3 -m edge_agent.metrics data/readings.sqlite
python3 scripts/run_recovery_experiment.py
python3 scripts/run_inference_experiment.py
python3 scripts/run_sampling_experiment.py
python3 scripts/run_batch_write_experiment.py
python3 scripts/run_stability_filter_experiment.py
python3 dashboard/app.py
python3 -m pytest
```

Open `dashboard/index.html` in a browser to inspect the current experiment summary.

## Example Results

These values come from the default deterministic synthetic sample.

| Metric | Result | Note |
| --- | ---: | --- |
| expected samples | 1800 | 30 minutes at 1 Hz |
| absent samples | 0 | no lost sequence slots |
| missing rate | 0.0344 | synthetic dropout |
| p95 latency | 132.089 ms | non-missing rows |
| uptime ratio | 0.9539 | ok rows / expected rows |
| recovery loss | 0 | base sample has no simulated write failure |

## Baseline vs Optimized

The current recovery experiment simulates a SQLite write failure for sequence
`600..719`. Direct writes lose those rows; the optimized path stores them in a
local JSONL buffer with a checkpoint and flushes them after recovery.

| Metric | Baseline direct write | Buffered recovery | Change |
| --- | ---: | ---: | ---: |
| observed samples | 1680 | 1800 | +120 |
| missing rate | 0.0989 | 0.0344 | -0.0645 |
| p95 latency | 125.789 ms | 132.089 ms | +6.300 ms |
| uptime ratio | 0.8900 | 0.9539 | +0.0639 |
| recovery loss | 120 samples | 0 samples | -120 |
| recovered rows | 0 | 120 | +120 |

This result is intentionally narrow: local buffering reduces recovery loss, but it
does not make the underlying synthetic dropout disappear.

## Lightweight Inference vs Quantized Scoring

The current inference experiment treats `status = noisy` as the ground-truth anomaly
label. It calibrates normal environmental ranges from synthetic `ok` readings, then
compares float-like anomaly scoring with quantized-like scoring.

| Metric | Float-like scoring | Quantized-like scoring | Change |
| --- | ---: | ---: | ---: |
| evaluated samples | 1738 | 1738 | 0 |
| true anomalies | 13 | 13 | 0 |
| true positives | 12 | 12 | 0 |
| false positives | 0 | 0 | 0 |
| false negatives | 1 | 1 | 0 |
| precision | 1.0000 | 1.0000 | 0 |
| recall | 0.9231 | 0.9231 | 0 |
| F1 | 0.9600 | 0.9600 | 0 |
| p95 inference latency | ~0.002 ms | ~0.001 ms | machine-dependent |
| model state size | 48 bytes | 6 bytes | -42 bytes |

This result is also intentionally narrow: quantized-like scoring reduces stored model
state in this small benchmark while preserving detection quality. Python-level timing
at this size is too small and variable to treat as hardware evidence; Raspberry Pi
measurements are needed before making stronger latency claims.

## Fixed Rate vs Adaptive Sampling

The current adaptive sampling experiment uses the quantized-like anomaly scorer. The
baseline evaluates every non-missing sample. The adaptive path samples every row at
startup, then samples every 2 sequence slots after 120 stable samples, and returns to
higher-frequency sampling for 30 samples after a detected anomaly.

| Metric | Fixed 1 Hz | Adaptive sampling | Change |
| --- | ---: | ---: | ---: |
| evaluated samples | 1738 | 1738 | 0 |
| sampled rows | 1738 | 1470 | -268 |
| skipped rows | 0 | 268 | +268 |
| estimated inference reduction | 0.0000 | 0.1542 | +15.42% |
| detected anomalies | 12 | 10 | -2 |
| missed anomalies | 1 | 3 | +2 |
| skipped anomalies | 0 | 2 | +2 |
| precision | 1.0000 | 1.0000 | 0 |
| recall | 0.9231 | 0.7692 | -0.1539 |
| F1 | 0.9600 | 0.8696 | -0.0904 |

This is a trade-off, not a free improvement: adaptive sampling reduces estimated
inference work by about 15%, but it misses more isolated noisy samples in the current
synthetic stream. The next step is to tune the policy and measure CPU, latency, and
power on target hardware.

## Direct Writes vs Batched SQLite Writes

The current batch-write experiment compares one-row SQLite writes against batches of
100 rows. The row count is the same in both cases.

| Metric | Direct per-row writes | Batched writes | Change |
| --- | ---: | ---: | ---: |
| rows written | 1800 | 1800 | 0 |
| batch size | 1 | 100 | +99 |
| insert calls | 1800 | 18 | -1782 |
| commit count | 1800 | 18 | -1782 |
| rows per commit | 1 | 100 | +99 |
| elapsed write time | ~5.5 s | ~67 ms | machine-dependent |

This result shows why batching matters for local storage: fewer commits can greatly
reduce write overhead. The timing is machine-dependent and should be re-measured on
Raspberry Pi before making hardware claims.

## Threshold Alerts vs Hysteresis Filter

The current stability-filter experiment creates a small synthetic challenge stream
with two transient spikes that should not count as true anomalies and one sustained
six-sample anomaly window. The baseline flags any row above the threshold. The
optimized path confirms an anomaly only after two consecutive threshold crossings.

| Metric | Threshold only | Hysteresis filter | Change |
| --- | ---: | ---: | ---: |
| evaluated samples | 120 | 120 | 0 |
| true anomalies | 6 | 6 | 0 |
| predicted anomalies | 8 | 5 | -3 |
| true positives | 6 | 5 | -1 |
| false positives | 2 | 0 | -2 |
| false negatives | 0 | 1 | +1 |
| precision | 0.7500 | 1.0000 | +0.2500 |
| recall | 1.0000 | 0.8333 | -0.1667 |
| F1 | 0.8571 | 0.9091 | +0.0520 |
| first detected anomaly seq | 95 | 96 | +1 sample |

This is another trade-off: a tiny hysteresis policy removes single-sample false
positives, but it delays sustained-anomaly confirmation by one sample and misses the
first row of that anomaly window.

## Planned Hardware

The first hardware target is:

- Raspberry Pi Zero 2 W
- BME280 temperature / humidity / pressure sensor
- local SQLite storage
- optional USB power meter

The project intentionally starts without hardware to validate the pipeline first.
Hardware is added later to expose real constraints such as CPU, memory, I/O,
thermal behavior, and optional power usage.

## Limitations

- v0 uses synthetic data only
- lightweight inference is statistical anomaly scoring, not a neural network
- adaptive sampling currently estimates inference-work reduction, not real power draw
- batch-write timing is machine-dependent until measured on target hardware
- hysteresis filtering is evaluated on a small synthetic challenge stream
- the dashboard is static HTML generated from local summary JSON files
- no cloud backend
- no large ML model
- no camera input
- no Kubernetes or distributed system layer
- no custom circuit board design

The focus is software-level reliability and optimization under constrained edge-like
conditions.

## Future Work

- connect BME280 sensor
- add MPU-6050 motion sensor
- add richer dashboard filtering or a Streamlit view if static HTML becomes limiting
- tune rolling-window / hysteresis anomaly filtering on real sensor data
- compare real sensor data with synthetic fault injection
- add local buffering and checkpoint recovery
- compare float32 vs quantized lightweight inference on Raspberry Pi
- tune fixed sampling vs adaptive sampling on Raspberry Pi
- re-measure direct vs batched SQLite writes on Raspberry Pi storage
- measure false-positive filtering and detection delay on real sensor streams
- add a short 90-second demo
