# Edge AI Reliability Benchmark

A student-scale systems project for checking whether a small edge-AI pipeline keeps
working when sensor-like data is missing, noisy, delayed, or interrupted.

In plain terms: this repository creates a small stream of environmental sensor data,
stores it locally, runs lightweight anomaly detection, intentionally introduces
failure cases, and compares simple software fixes against baseline behavior.

The current version uses synthetic data on a laptop. That is intentional: the goal is
to make the measurement and optimization loop reproducible before moving the same
pipeline onto Raspberry Pi hardware and real sensors.

## Current Status

| Area | Current implementation |
| --- | --- |
| Data source | Deterministic synthetic temperature / humidity / pressure stream |
| Storage | Local SQLite readings table |
| Inference | Lightweight statistical anomaly scoring, not a neural network yet |
| Reliability metrics | Missing rate, p95 latency, uptime ratio, recovery loss |
| Optimization experiments | Local buffer, batch writes, quantized-like scoring, adaptive sampling, hysteresis filter |
| Dashboard | Dependency-free static HTML generated from local experiment summaries |
| Cost / cloud | No paid API, no cloud backend, no external service dependency |

## What This Demonstrates

This project is not trying to be a polished edge-AI product. It is a compact benchmark
for the engineering questions that appear before a product exists:

- What happens when local writes fail?
- How much data can a checkpoint buffer recover?
- Can a smaller inference state preserve detection quality?
- How much inference work can be skipped before recall drops?
- How much overhead comes from committing every SQLite row separately?
- Can a tiny stability filter remove transient false alerts, and what delay does it add?

The important part is the comparison shape:

```text
baseline behavior -> software optimization -> measured trade-off
```

## Local Demo

Run everything locally. The commands below generate synthetic data, run the experiments,
build the static dashboard, and run the test suite.

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

Then open:

```text
dashboard/index.html
```

The generated SQLite databases, summary folders, and dashboard HTML are local artifacts
and are ignored by git.

## Pipeline

```text
synthetic sensor-like data
  -> CSV
  -> SQLite
  -> reliability metrics
  -> lightweight anomaly detection
  -> software optimization experiments
  -> local dashboard
  -> experiment notes
```

The current data simulates 30 minutes of 1 Hz environmental readings with temperature,
humidity, pressure, latency jitter, dropout, noisy readings, and restart-gap markers.

## Results Snapshot

These values come from the default deterministic synthetic sample. They are useful for
comparing software behavior, not for claiming real hardware performance.

| Experiment | Baseline | Optimized / alternate path | Main result | Trade-off / limit |
| --- | ---: | ---: | --- | --- |
| Local write failure | 120 rows lost | 0 rows lost | JSONL buffer + checkpoint recovers the failed write window | Does not remove unrelated synthetic dropout |
| Quantized-like scoring | 48 B state, F1 0.9600 | 6 B state, F1 0.9600 | Smaller stored state with same detection quality on this sample | Python timing is too small for hardware claims |
| Adaptive sampling | 1738 sampled rows, F1 0.9600 | 1470 sampled rows, F1 0.8696 | About 15.42% fewer inferred rows | Recall drops because isolated anomalies can be skipped |
| Batch SQLite writes | 1800 commits | 18 commits | Commit count drops by 1782 | Wall-clock timing must be re-measured on target storage |
| Hysteresis filter | 2 false positives, recall 1.0000 | 0 false positives, recall 0.8333 | Single-sample false alerts are removed | Sustained anomaly confirmation is delayed by 1 sample |

More detail is in:

- `experiments/baseline_vs_optimized.md`
- `experiments/inference_quantization.md`
- `experiments/adaptive_sampling.md`
- `experiments/batch_writes.md`
- `experiments/stability_filter.md`
- `experiments/dashboard.md`
- `docs/experiment_log.md`

## Technical Core

The repository is organized around small, testable pieces:

| Path | Role |
| --- | --- |
| `scripts/generate_synthetic_data.py` | Generates deterministic sensor-like CSV data |
| `edge_agent/storage.py` | Loads readings into SQLite |
| `edge_agent/metrics.py` | Calculates reliability metrics |
| `edge_agent/buffer.py` | Implements local JSONL buffering and checkpoints |
| `edge_agent/inference.py` | Implements float-like and quantized-like anomaly scoring |
| `edge_agent/sampling.py` | Implements fixed-rate vs adaptive sampling comparison |
| `edge_agent/batching.py` | Compares per-row vs batched SQLite writes |
| `edge_agent/stability_filter.py` | Compares threshold alerts vs hysteresis filtering |
| `dashboard/app.py` | Builds a static HTML report from local summary JSON files |
| `tests/` | Covers metrics, recovery buffer, inference, sampling, batching, filtering, and dashboard generation |

## Metrics

| Metric | Meaning |
| --- | --- |
| `missing_rate` | Fraction of expected samples that are missing or absent |
| `p95_latency_ms` | 95th percentile latency for non-missing readings |
| `uptime_ratio` | Fraction of expected samples that are normal `ok` readings |
| `recovery_loss` | Expected sequence slots absent after a simulated write failure |
| `precision` / `recall` / `f1` | Detection quality for synthetic anomaly labels |
| `model_state_bytes` | Approximate stored state size for the lightweight scorer |
| `sampled_count` / `skipped_count` | How many rows are evaluated or skipped by sampling policy |
| `commit_count` | Number of SQLite commits used for a write path |
| `false_positive` | Normal or transient rows incorrectly flagged as anomalies |
| `detection_delay_samples` | How many samples later a filtered alert is confirmed |

## Why This Is Engineering-Focused

The scope is intentionally small, but the benchmark is built around real systems
trade-offs:

- Results are reproducible from deterministic input data.
- Each optimization is compared against a baseline.
- Improvements are not presented as free wins; the README records the cost when recall,
  latency, or evidence strength changes.
- The code is split into small modules with tests and a GitHub Actions workflow.
- The project avoids inflated claims until the same measurements run on target hardware.

## Scope and Limits

Current limitations:

- Synthetic data only.
- Lightweight statistical scoring only; no neural network model yet.
- Adaptive sampling estimates inference-work reduction; it does not measure real CPU or
  power draw yet.
- Batch-write timing is machine-dependent until repeated on Raspberry Pi storage.
- Stability filtering is tested on a small synthetic challenge stream.
- The dashboard is a static local report, not a hosted web app.

Intentionally out of scope for now:

- Cloud backend
- Paid APIs
- Camera input
- Kubernetes or distributed orchestration
- Custom circuit-board design
- Claims about production safety or hardware latency before target-device measurement

## Planned Hardware Path

The first hardware target is deliberately modest:

| Part | Purpose |
| --- | --- |
| Raspberry Pi Zero 2 W | Constrained compute target |
| BME280 | Temperature / humidity / pressure sensor |
| SQLite on local storage | Local persistence under write constraints |
| Optional USB power meter | Power comparison if available |

The next defensible step is to run the same experiments on Raspberry Pi and record CPU,
memory, wall-clock latency, storage behavior, and optional power usage.

## Publication and Security Notes

This repository is designed to be safe to show publicly in its current form:

- The tracked sample data is synthetic.
- There are no credentials, API keys, tokens, private endpoints, or personal datasets
  required by the benchmark.
- The project runs locally and does not send data to an external service.
- Generated SQLite databases, experiment output folders, virtual environments, and the
  generated dashboard HTML are ignored by git.
- Future real sensor captures should be reviewed before committing, especially if they
  include location, device identifiers, personal environment data, or timestamps that
  should not be public.

Before publishing a new version, run the tests and inspect the tracked file set:

```bash
git status --short
git ls-files
python3 -m pytest
```

## License

No license file is currently included. Add one before inviting external reuse.
