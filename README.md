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

This project implements a minimal edge AI reliability and optimization pipeline:

1. Generate or collect sensor-like data
2. Store readings locally in SQLite
3. Measure reliability metrics
4. Run lightweight anomaly detection
5. Apply software-level optimizations
6. Compare baseline vs optimized results
7. Explain results with reproducible logs and a dashboard

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

`v0` uses synthetic environmental sensor data instead of real hardware.
The goal is to make the reliability pipeline measurable before adding Raspberry Pi
hardware, lightweight inference, and optimization experiments.

The current v0 flow is:

```text
synthetic sensor data
  -> CSV
  -> SQLite readings table
  -> reliability metrics
  -> README explanation
```

## Metrics

| Metric | Meaning |
| --- | --- |
| `missing_rate` | Fraction of expected samples that are missing |
| `p95_latency_ms` | 95th percentile of non-missing sample latency |
| `uptime_ratio` | Fraction of expected samples that are normal `ok` readings |
| `inference_latency_ms` | Time spent in lightweight anomaly detection |
| `memory_mb` | Approximate memory usage during inference |
| `recovery_loss` | Samples lost after restart or interruption |

The v0 implementation calculates `missing_rate`, `p95_latency_ms`, and
`uptime_ratio`. Inference and optimization metrics are planned for later versions.

## Optimization Plan

The project does not stop at measurement. The final goal is to compare a baseline
pipeline against software-level optimizations.

| Problem | Optimization | Main Metrics |
| --- | --- | --- |
| missing samples or restart loss | local buffer / checkpoint | missing rate / recovery loss |
| storage latency | batch writes | p95 latency / write count |
| heavy inference | quantization / smaller model | inference latency / memory / accuracy drop |
| wasted work during normal periods | adaptive sampling | CPU / power / event detection quality |

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
python3 scripts/generate_synthetic_data.py
python3 -m edge_agent.storage data/sample.csv data/readings.sqlite
python3 -m edge_agent.metrics data/readings.sqlite
pytest
```

## Example Results

These values come from the default deterministic synthetic sample.

| Metric | Result | Note |
| --- | ---: | --- |
| expected samples | 1800 | 30 minutes at 1 Hz |
| missing rate | 0.0344 | synthetic dropout |
| p95 latency | 132.089 ms | non-missing rows |
| uptime ratio | 0.9539 | ok rows / expected rows |

## Baseline vs Optimized

| Metric | Baseline | Optimized | Change |
| --- | ---: | ---: | ---: |
| missing rate | TBD | TBD | TBD |
| p95 latency | TBD ms | TBD ms | TBD |
| inference latency | TBD ms | TBD ms | TBD |
| memory usage | TBD MB | TBD MB | TBD |
| recovery loss | TBD samples | TBD samples | TBD |

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
- add Streamlit dashboard
- add anomaly detection with rolling z-score
- compare real sensor data with synthetic fault injection
- add local buffering and checkpoint recovery
- compare float32 vs quantized lightweight inference
- compare fixed sampling vs adaptive sampling
- add a short 90-second demo
