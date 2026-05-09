# Inference Quantization Experiment

## Scope

This is a lightweight anomaly scoring experiment, not a neural network benchmark.
The goal is to add an inference stage to the reliability pipeline and compare
float-like scoring against quantized-like scoring before moving to Raspberry Pi.

## Method

1. Load `data/sample.csv`.
2. Use normal `ok` rows for calibration.
3. Treat `status = noisy` as the ground-truth anomaly label.
4. Score non-missing rows with a float-like z-score scorer.
5. Score the same rows with a quantized-like integer scorer.
6. Compare detection quality, p95 inference latency, and model state size.

## Result

| Metric | Float-like scoring | Quantized-like scoring |
| --- | ---: | ---: |
| evaluated samples | 1738 | 1738 |
| true anomalies | 13 | 13 |
| predicted anomalies | 12 | 12 |
| true positives | 12 | 12 |
| false positives | 0 | 0 |
| false negatives | 1 | 1 |
| precision | 1.0000 | 1.0000 |
| recall | 0.9231 | 0.9231 |
| F1 | 0.9600 | 0.9600 |
| average inference latency | ~0.001 ms | ~0.001 ms |
| p95 inference latency | ~0.002 ms | ~0.001 ms |
| model state size | 48 bytes | 6 bytes |

## Interpretation

Quantized-like scoring preserved detection quality and reduced stored state size in
the synthetic benchmark. The latency numbers are too small and Python-dependent to use
as hardware evidence. The follow-up v7 experiment adds a standard-library tiny learned
model; hardware CPU, memory, and wall-clock latency should still wait for Raspberry Pi
measurements.
