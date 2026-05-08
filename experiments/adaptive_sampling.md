# Adaptive Sampling Experiment

## Scope

This experiment compares fixed 1 Hz inference against adaptive sampling. It uses the
quantized-like anomaly scorer from the v2 inference experiment.

This is not a real power benchmark yet. It estimates inference-work reduction by
counting how many rows are sampled or skipped. CPU, wall-clock latency, and power need
to be measured on Raspberry Pi before making hardware claims.

## Policy

The adaptive policy is intentionally simple:

1. Sample every row at startup.
2. After 120 stable sampled rows, sample every 2 sequence slots.
3. If an anomaly is detected, return to every-row sampling for 30 samples.
4. Count skipped ground-truth noisy rows as missed anomalies.

## Result

| Metric | Fixed 1 Hz | Adaptive sampling |
| --- | ---: | ---: |
| evaluated samples | 1738 | 1738 |
| sampled rows | 1738 | 1470 |
| skipped rows | 0 | 268 |
| sampling ratio | 1.0000 | 0.8458 |
| estimated inference reduction | 0.0000 | 0.1542 |
| true anomalies | 13 | 13 |
| detected anomalies | 12 | 10 |
| missed anomalies | 1 | 3 |
| skipped anomalies | 0 | 2 |
| false positives | 0 | 0 |
| precision | 1.0000 | 1.0000 |
| recall | 0.9231 | 0.7692 |
| F1 | 0.9600 | 0.8696 |

## Interpretation

Adaptive sampling reduced estimated inference work by about 15%, but it missed more
isolated noisy samples. This is a useful systems trade-off:

```text
Less inference work can reduce CPU and power demand, but lower sampling frequency can
miss short anomalies.
```

The next defensible step is to run this on Raspberry Pi and record CPU, memory,
wall-clock latency, and optional USB power measurements.
