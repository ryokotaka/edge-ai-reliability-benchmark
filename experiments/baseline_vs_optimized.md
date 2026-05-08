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
