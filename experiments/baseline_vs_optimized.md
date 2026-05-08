# Baseline vs Optimized

## v1 Local Buffer / Checkpoint Recovery

The first optimization experiment simulates a SQLite write failure for sequence
`600..719`. The baseline direct-write path loses those rows. The optimized path
writes them to a local JSONL buffer, records a checkpoint, and flushes them to
SQLite after recovery.

| Metric | Baseline direct write | Buffered recovery | Interpretation |
| --- | ---: | ---: | --- |
| observed samples | 1680 | 1800 | local buffer recovered the write-failure window |
| missing rate | 0.0989 | 0.0344 | recovery removed absent sequence slots |
| p95 latency | 125.789 ms | 132.089 ms | recovered rows include original jitter distribution |
| uptime ratio | 0.8900 | 0.9539 | recovered ok rows restore uptime accounting |
| recovery loss | 120 samples | 0 samples | checkpoint recovery effect |

## Planned Later Comparisons

| Metric | Baseline | Optimized | Interpretation |
| --- | ---: | ---: | --- |
| inference latency on Raspberry Pi | TBD ms | TBD ms | quantization effect on target hardware |
| memory usage on Raspberry Pi | TBD MB | TBD MB | constrained-device fit |
| adaptive sampling CPU / power | TBD | TBD | target-hardware sampling trade-off |
| batch SQLite writes on Raspberry Pi | TBD ms | TBD ms | target-storage write overhead |
| hysteresis filter on real sensor data | TBD | TBD | false-positive / detection-delay trade-off |

## v2 Float-like vs Quantized-like Anomaly Scoring

The second optimization experiment uses `status = noisy` as the ground-truth anomaly
label. It calibrates normal environmental ranges from synthetic `ok` rows and compares
float-like scoring with quantized-like scoring.

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

Interpretation:

```text
Quantized-like scoring preserved detection quality and reduced stored model state
in this small synthetic benchmark. Timing must be re-measured on Raspberry Pi before
claiming target-device latency improvement.
```

## v3 Fixed 1 Hz vs Adaptive Sampling

The third optimization experiment uses the quantized-like anomaly scorer. The baseline
evaluates every non-missing row. The adaptive policy samples every row during startup,
then samples every 2 sequence slots after 120 stable samples, and holds high-frequency
sampling for 30 samples after a detected anomaly.

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

Interpretation:

```text
Adaptive sampling reduced estimated inference work by about 15%, but recall and F1
dropped because isolated noisy rows can be skipped. This is useful as a trade-off
experiment, not as a final policy. The next version should tune the policy on target
hardware and add CPU / power measurements.
```

## v4 Direct SQLite Writes vs Batched SQLite Writes

The fourth optimization experiment compares one-row SQLite writes against batched
writes of 100 rows. Both paths write the same 1800 synthetic readings.

| Metric | Direct per-row writes | Batched writes | Interpretation |
| --- | ---: | ---: | --- |
| rows written | 1800 | 1800 | same data |
| batch size | 1 | 100 | optimized path groups rows |
| insert calls | 1800 | 18 | fewer write calls |
| commit count | 1800 | 18 | fewer durable commits |
| rows per insert call | 1 | 100 | less per-row overhead |
| rows per commit | 1 | 100 | less commit overhead |
| elapsed write time | ~5.5 s | ~67 ms | local-machine example only |

Interpretation:

```text
Batch writes dramatically reduce SQLite insert and commit overhead in the synthetic
benchmark. The stable claim is the write-call and commit-count reduction; elapsed time
must be re-measured on Raspberry Pi storage before making hardware claims.
```

## v5 Threshold Alerts vs Hysteresis Filter

The fifth optimization experiment uses a small synthetic challenge stream with two
single-sample transient spikes and one sustained six-sample noisy window. The baseline
flags every threshold crossing. The optimized path requires two consecutive anomaly
scores before confirming an alert.

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

Interpretation:

```text
A small hysteresis filter removed transient false positives, but it delayed confirmed
detection by one sample. This is useful for explaining false-positive control as a
trade-off, not as a universally better detector.
```
