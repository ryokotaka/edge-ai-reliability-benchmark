# Edge AI Reliability Benchmark

A student-scale systems project for checking whether a small edge-AI-style sensor
inference pipeline keeps working when data is missing, noisy, delayed, or interrupted.

In plain terms: this repository creates a small stream of environmental sensor data,
stores it locally, runs lightweight anomaly detection and a tiny learned model,
intentionally introduces failure cases, and compares simple software fixes against
baseline behavior.

The current version uses synthetic data on a laptop. That is intentional: the goal is
to make the measurement and optimization loop reproducible before moving the same
pipeline onto Raspberry Pi hardware and real sensors.

## Current Status

| Area | Current implementation |
| --- | --- |
| Data source | Deterministic synthetic temperature / humidity / pressure stream |
| Storage | Local SQLite readings table |
| Inference | Lightweight statistical scoring and a standard-library tiny learned model |
| Reliability metrics | Missing rate, p95 latency, uptime ratio, recovery loss |
| Optimization experiments | Local buffer, batch writes, quantized-like scoring, tiny model quantization/stress test, resource budget gate, exported model artifact, adaptive sampling, hysteresis filter |
| Dashboard | Dependency-free static HTML generated from local experiment summaries |
| Cost / cloud | No paid API, no cloud backend, no external service dependency |

## What This Demonstrates

This project is not trying to be a polished edge-AI product. It is a compact benchmark
for the engineering questions that appear before a product exists:

- What happens when local writes fail?
- How much data can a checkpoint buffer recover?
- Can a smaller inference state preserve detection quality?
- Can a trainable tiny model match the statistical scorer on held-out synthetic data?
- Does that tiny-model result survive multiple synthetic seeds?
- Which model still passes a small edge-style resource budget?
- Can the selected tiny model be exported and loaded without retraining?
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
python3 scripts/run_tiny_model_experiment.py
python3 scripts/run_tiny_model_stress_experiment.py
python3 scripts/run_resource_budget_experiment.py
python3 scripts/run_model_artifact_experiment.py
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
  -> tiny learned sensor model
  -> exported quantized model artifact
  -> software optimization experiments
  -> local dashboard
  -> experiment notes
```

The current data simulates 30 minutes of 1 Hz environmental readings with temperature,
humidity, pressure, latency jitter, dropout, noisy readings, and restart-gap markers.

## Results Snapshot

Most values come from the default deterministic synthetic sample. The stress-test row
uses multiple deterministic synthetic seeds. These values are useful for comparing
software behavior, not for claiming real hardware performance.

| Experiment | Baseline | Optimized / alternate path | Main result | Trade-off / limit |
| --- | ---: | ---: | --- | --- |
| Local write failure | 120 rows lost | 0 rows lost | JSONL buffer + checkpoint recovers the failed write window | Does not remove unrelated synthetic dropout |
| Quantized-like scoring | 48 B state, F1 0.9600 | 6 B state, F1 0.9600 | Smaller stored state with same detection quality on this sample | Python timing is too small for hardware claims |
| Tiny learned model | 104 B state, F1 1.0000 | 42 B state, F1 1.0000 | Quantized learned model matches float learned model on the held-out split | Synthetic test split has only 3 anomaly rows |
| Tiny model stress test | Statistical F1 0.8767 | Quantized learned F1 0.9487 | 7 deterministic seeds cover 41 held-out anomaly rows | Still synthetic; no hardware timing claim |
| Resource budget gate | Max state 64 B, min F1 0.9000 | Quantized tiny model passes | Float model fails state budget; statistical scorer fails quality budget | Budget is a proxy, not measured RAM/CPU |
| Model artifact runtime | In-memory quantized F1 1.0000 | Loaded artifact F1 1.0000 | Exported JSON artifact reloads with 0 prediction mismatches | JSON file size is not compact binary deployment size |
| Adaptive sampling | 1738 sampled rows, F1 0.9600 | 1470 sampled rows, F1 0.8696 | About 15.42% fewer inferred rows | Recall drops because isolated anomalies can be skipped |
| Batch SQLite writes | 1800 commits | 18 commits | Commit count drops by 1782 | Wall-clock timing must be re-measured on target storage |
| Hysteresis filter | 2 false positives, recall 1.0000 | 0 false positives, recall 0.8333 | Single-sample false alerts are removed | Sustained anomaly confirmation is delayed by 1 sample |

## Detailed Experiment Results

The README keeps the full result tables close to the project overview because many
readers will not open separate experiment files. Each section is collapsed by default
so the top-level README stays skimmable.

<details>
<summary><strong>v1 Local Buffer / Checkpoint Recovery</strong></summary>

This experiment simulates a SQLite write failure for sequence `600..719`. The baseline
direct-write path loses those rows. The optimized path writes them to a local JSONL
buffer, records a checkpoint, and flushes them to SQLite after recovery.

| Metric | Baseline direct write | Buffered recovery | Interpretation |
| --- | ---: | ---: | --- |
| observed samples | 1680 | 1800 | local buffer recovered the write-failure window |
| missing rate | 0.0989 | 0.0344 | recovery removed absent sequence slots |
| p95 latency | 125.789 ms | 132.089 ms | recovered rows include original jitter distribution |
| uptime ratio | 0.8900 | 0.9539 | recovered ok rows restore uptime accounting |
| recovery loss | 120 samples | 0 samples | checkpoint recovery effect |

This is intentionally narrow: buffering reduces recovery loss, but it does not remove
the unrelated synthetic dropout already present in the stream.

</details>

<details>
<summary><strong>v2 Float-like vs Quantized-like Anomaly Scoring</strong></summary>

This is lightweight anomaly scoring, not a neural-network benchmark. It treats
`status = noisy` as the synthetic ground-truth anomaly label and compares float-like
scoring with quantized-like integer scoring.

| Metric | Float-like scoring | Quantized-like scoring | Interpretation |
| --- | ---: | ---: | --- |
| evaluated samples | 1738 | 1738 | missing rows are excluded from inference |
| true anomalies | 13 | 13 | synthetic noisy rows |
| true positives | 12 | 12 | same detected anomalies |
| false positives | 0 | 0 | no normal rows flagged |
| false negatives | 1 | 1 | one noisy row below threshold |
| precision | 1.0000 | 1.0000 | no false positives |
| recall | 0.9231 | 0.9231 | one missed noisy row |
| F1 | 0.9600 | 0.9600 | detection quality preserved |
| p95 inference latency | ~0.002 ms | ~0.001 ms | Python-level timing only |
| model state size | 48 bytes | 6 bytes | quantized-like state is smaller |

Quantized-like scoring preserved detection quality and reduced stored state size in
this synthetic benchmark. The timing numbers are too small and Python-dependent to use
as hardware evidence.

</details>

<details>
<summary><strong>v7 Statistical Scorer vs Tiny Learned Sensor Model</strong></summary>

This experiment adds a small trainable classifier without external ML libraries. It
uses a fixed chronological split: 1216 train rows and 522 test rows. The label is
`status = noisy` or `fault_type = noise`; the input features are normalized deviations
from normal temperature, humidity, pressure, and latency values.

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| evaluated samples | 522 | 522 | 522 |
| true anomalies | 3 | 3 | 3 |
| true positives | 3 | 3 | 3 |
| false positives | 0 | 0 | 0 |
| false negatives | 0 | 0 | 0 |
| precision | 1.0000 | 1.0000 | 1.0000 |
| recall | 1.0000 | 1.0000 | 1.0000 |
| F1 | 1.0000 | 1.0000 | 1.0000 |
| p95 inference latency | ~0.001 ms | ~0.002 ms | ~0.002 ms |
| model state size | 48 bytes | 104 bytes | 42 bytes |

This is a TinyML-style baseline, not a neural-network framework or hardware inference
runtime. The held-out split is small and synthetic, so the result should be read as a
local reproducibility step: the project now has a trainable inference stage that can
be moved to target hardware later.

</details>

<details>
<summary><strong>v8 Tiny Model Multi-Seed Stress Test</strong></summary>

This experiment repeats the tiny learned model comparison across 7 deterministic
synthetic seeds: `11, 23, 42, 71, 101, 133, 191`. It keeps the same 70/30 chronological
train/test split for each seed and aggregates the held-out results.

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| seeds | 7 | 7 | 7 |
| held-out rows | 3676 | 3676 | 3676 |
| held-out anomalies | 41 | 41 | 41 |
| true positives | 32 | 37 | 37 |
| false positives | 0 | 0 | 0 |
| false negatives | 9 | 4 | 4 |
| precision | 1.0000 | 1.0000 | 1.0000 |
| recall | 0.7805 | 0.9024 | 0.9024 |
| aggregate F1 | 0.8767 | 0.9487 | 0.9487 |
| mean seed F1 | 0.8849 | 0.9558 | 0.9558 |
| minimum seed F1 | 0.7273 | 0.8333 | 0.8333 |
| model state size | 48 bytes | 104 bytes | 42 bytes |

This reduces the chance that the v7 result is only a lucky split. It is still a
synthetic stress test, so it strengthens reproducibility evidence but does not replace
target-device measurement.

</details>

<details>
<summary><strong>v9 Resource Budget Gate</strong></summary>

This experiment turns the multi-seed tiny-model result into a small edge-style budget
check. It does not measure real RAM, CPU, or power. Instead, it makes the current
trade-off explicit by asking which model fits a strict stored-state budget while
keeping detection quality above a fixed threshold.

| Budget item | Threshold |
| --- | ---: |
| model state size | <= 64 bytes |
| aggregate F1 | >= 0.9000 |
| false-negative rate | <= 10.00% |
| false positives | <= 0 |

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| model state size | 48 bytes | 104 bytes | 42 bytes |
| aggregate F1 | 0.8767 | 0.9487 | 0.9487 |
| false-negative rate | 21.95% | 9.76% | 9.76% |
| false positives | 0 | 0 | 0 |
| state budget | pass | fail | pass |
| F1 budget | fail | pass | pass |
| false-negative budget | fail | pass | pass |
| all budgets | fail | fail | pass |

Under this proxy budget, the quantized tiny model is the only model that passes all
checks. This is useful for explaining the engineering decision, but it should not be
presented as measured hardware resource usage.

</details>

<details>
<summary><strong>v10 Exported Quantized Model Artifact</strong></summary>

This experiment checks the next deployment-shaped step: train and quantize the tiny
model once, export only the quantized runtime state, load that artifact back, and run
inference without retraining.

The artifact is JSON so it stays easy to inspect in a student project. The important
runtime state is still the 42-byte quantized model state; the 929-byte JSON file size
is a readable storage format, not a claim about compact binary deployment.

| Metric | In-memory quantized model | Loaded artifact |
| --- | ---: | ---: |
| evaluated samples | 522 | 522 |
| true anomalies | 3 | 3 |
| true positives | 3 | 3 |
| false positives | 0 | 0 |
| false negatives | 0 | 0 |
| precision | 1.0000 | 1.0000 |
| recall | 1.0000 | 1.0000 |
| F1 | 1.0000 | 1.0000 |
| model state size | 42 bytes | 42 bytes |
| prediction mismatches | 0 | 0 |
| max probability difference | 0.0000 | 0.0000 |

This does not make hardware claims. It makes the runtime boundary clearer: the device
side can be shaped as `load small model state -> infer`, while training remains an
offline local step.

</details>

<details>
<summary><strong>v3 Fixed 1 Hz vs Adaptive Sampling</strong></summary>

This experiment uses the quantized-like anomaly scorer. The baseline evaluates every
non-missing row. The adaptive policy samples every row during startup, then samples
every 2 sequence slots after 120 stable samples, and temporarily returns to every-row
sampling after a detected anomaly.

| Metric | Fixed 1 Hz | Adaptive sampling | Interpretation |
| --- | ---: | ---: | --- |
| evaluated samples | 1738 | 1738 | same non-missing stream |
| sampled rows | 1738 | 1470 | adaptive policy skipped stable rows |
| skipped rows | 0 | 268 | fewer inference calls |
| estimated inference reduction | 0.0000 | 0.1542 | about 15% less inference work |
| true anomalies | 13 | 13 | same ground truth |
| detected anomalies | 12 | 10 | adaptive missed more isolated noisy rows |
| missed anomalies | 1 | 3 | detection-quality cost |
| skipped anomalies | 0 | 2 | sampling policy skipped two noisy rows |
| precision | 1.0000 | 1.0000 | no false positives |
| recall | 0.9231 | 0.7692 | recall dropped |
| F1 | 0.9600 | 0.8696 | quality/work trade-off |

Adaptive sampling reduced estimated inference work by about 15%, but recall and F1
dropped because isolated noisy rows can be skipped. This is a trade-off experiment,
not a final policy.

</details>

<details>
<summary><strong>v4 Direct SQLite Writes vs Batched SQLite Writes</strong></summary>

This experiment compares one-row SQLite writes against batched writes of 100 rows.
Both paths write the same 1800 synthetic readings.

| Metric | Direct per-row writes | Batched writes | Interpretation |
| --- | ---: | ---: | --- |
| rows written | 1800 | 1800 | same data |
| batch size | 1 | 100 | optimized path groups rows |
| insert calls | 1800 | 18 | fewer write calls |
| commit count | 1800 | 18 | fewer durable commits |
| rows per insert call | 1 | 100 | less per-row overhead |
| rows per commit | 1 | 100 | less commit overhead |
| elapsed write time | ~5.5 s | ~67 ms | local-machine example only |

The stable result is the reduction in insert calls and commit count. Wall-clock timing
must be repeated on Raspberry Pi storage before making hardware-performance claims.

</details>

<details>
<summary><strong>v5 Threshold Alerts vs Hysteresis Filter</strong></summary>

This experiment uses a small synthetic challenge stream with two single-sample
transient spikes and one sustained six-sample noisy window. The baseline flags every
threshold crossing. The optimized path requires two consecutive anomaly scores before
confirming an alert.

| Metric | Threshold only | Hysteresis filter | Interpretation |
| --- | ---: | ---: | --- |
| evaluated samples | 120 | 120 | same challenge stream |
| true anomalies | 6 | 6 | sustained noisy window |
| predicted anomalies | 8 | 5 | fewer alerts |
| true positives | 6 | 5 | first sustained anomaly row is delayed |
| false positives | 2 | 0 | single-sample transient spikes are suppressed |
| false negatives | 0 | 1 | detection delay creates one missed sample |
| precision | 0.7500 | 1.0000 | fewer false alerts |
| recall | 1.0000 | 0.8333 | less immediate detection |
| F1 | 0.8571 | 0.9091 | better balance on this synthetic stream |
| first detected anomaly seq | 95 | 96 | one-sample confirmation delay |

The hysteresis filter removed transient false positives, but it delayed confirmed
detection by one sample. This is useful for explaining false-positive control as a
trade-off, not as a universally better detector.

</details>

The same result trail is also kept in separate notes:

- `experiments/baseline_vs_optimized.md`
- `experiments/inference_quantization.md`
- `experiments/tiny_model.md`
- `experiments/tiny_model_stress.md`
- `experiments/resource_budget.md`
- `experiments/model_artifact.md`
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
| `edge_agent/tiny_model.py` | Trains and compares a tiny learned sensor classifier |
| `edge_agent/tiny_model_stress.py` | Aggregates tiny model results across multiple synthetic seeds |
| `edge_agent/resource_budget.py` | Checks model choices against a proxy edge-style resource budget |
| `edge_agent/model_artifact.py` | Exports and reloads the quantized tiny model runtime state |
| `edge_agent/sampling.py` | Implements fixed-rate vs adaptive sampling comparison |
| `edge_agent/batching.py` | Compares per-row vs batched SQLite writes |
| `edge_agent/stability_filter.py` | Compares threshold alerts vs hysteresis filtering |
| `dashboard/app.py` | Builds a static HTML report from local summary JSON files |
| `tests/` | Covers metrics, recovery buffer, inference, tiny-model stress aggregation, model artifacts, sampling, batching, filtering, and dashboard generation |

## Metrics

| Metric | Meaning |
| --- | --- |
| `missing_rate` | Fraction of expected samples that are missing or absent |
| `p95_latency_ms` | 95th percentile latency for non-missing readings |
| `uptime_ratio` | Fraction of expected samples that are normal `ok` readings |
| `recovery_loss` | Expected sequence slots absent after a simulated write failure |
| `precision` / `recall` / `f1` | Detection quality for synthetic anomaly labels |
| `model_state_bytes` | Approximate stored state size for the lightweight scorer or tiny model |
| `sampled_count` / `skipped_count` | How many rows are evaluated or skipped by sampling policy |
| `commit_count` | Number of SQLite commits used for a write path |
| `false_positive` | Normal or transient rows incorrectly flagged as anomalies |
| `detection_delay_samples` | How many samples later a filtered alert is confirmed |
| `mean_seed_f1` / `min_seed_f1` | Multi-seed stress-test stability indicators |
| `passes_all` | Whether a model clears all configured resource-budget checks |
| `prediction_mismatch_count` | Difference between in-memory model predictions and loaded artifact predictions |

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
- Tiny learned model is a standard-library logistic classifier; the multi-seed stress
  test is still synthetic and has no neural-network framework or hardware inference
  runtime yet.
- Resource budget checks are proxy thresholds, not measured RAM, CPU, or power usage.
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

MIT License. See `LICENSE`.
