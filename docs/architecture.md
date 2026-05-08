# Architecture

```text
synthetic sensor data
  -> CSV
  -> SQLite readings table
  -> reliability metrics
  -> lightweight inference
  -> software optimization
  -> experiment log
```

v0 stops at CSV, SQLite, and reliability metrics. Lightweight inference and
optimization are planned after the measurement pipeline is reproducible.

v1 adds a local JSONL recovery buffer:

```text
synthetic sensor data
  -> simulated SQLite write failure
  -> local recovery buffer
  -> checkpoint
  -> SQLite flush after recovery
  -> recovery_loss comparison
```

v2 adds lightweight anomaly scoring:

```text
synthetic sensor data
  -> calibration from normal rows
  -> float-like anomaly scorer
  -> quantized-like anomaly scorer
  -> precision / recall / F1 / state-size comparison
```

v3 adds adaptive sampling:

```text
quantized-like anomaly scorer
  -> fixed-rate baseline
  -> adaptive stable-period skipping
  -> sampled_count / recall / F1 comparison
```

v4 adds batch-write comparison:

```text
CSV readings
  -> direct per-row SQLite writes
  -> batched SQLite writes
  -> insert_calls / commit_count / elapsed_ms comparison
```

v5 adds a stability filter for transient false positives:

```text
synthetic transient spikes
  -> threshold-only anomaly alerts
  -> consecutive-anomaly hysteresis filter
  -> false_positive / recall / detection_delay comparison
```
