# Tiny Learned Sensor Model Experiment

## Scope

This experiment adds a small trainable sensor classifier to the local benchmark. It is
a TinyML-style baseline, not a neural-network framework, TensorFlow Lite model, or
hardware inference runtime.

The goal is to move from `sensor data -> statistical score` toward:

```text
sensor data -> trainable tiny model -> inference -> quantized-like model state
```

## Method

1. Load `data/sample.csv`.
2. Keep non-missing rows with temperature, humidity, pressure, and latency values.
3. Split rows chronologically: 70% train, 30% test.
4. Treat `status = noisy` or `fault_type = noise` as the anomaly label.
5. Build normalized deviation features from normal training rows.
6. Train a standard-library logistic classifier with a fixed positive-class weight.
7. Convert the learned model to a quantized-like integer state.
8. Compare the existing statistical scorer, the float learned model, and the
   quantized learned model on the held-out test split.

## Result

| Metric | Statistical scorer | Float tiny model | Quantized tiny model |
| --- | ---: | ---: | ---: |
| train rows | 1216 | 1216 | 1216 |
| test rows | 522 | 522 | 522 |
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

## Interpretation

The learned model and quantized learned model matched the statistical scorer on the
held-out synthetic split. The quantized learned state is smaller than the float learned
state while preserving the same detection quality on this sample.

This result should stay modest: the test split has only 3 anomaly rows, and Python
timing is too small for hardware-performance claims. The value of v7 is that the
benchmark now has a trainable inference stage that can later be measured on constrained
hardware with the same before / after structure.
