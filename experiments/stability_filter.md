# Stability Filter Experiment

## Scope

This experiment compares threshold-only anomaly alerts against a tiny hysteresis
filter. It uses a synthetic challenge stream with:

- two single-sample transient spikes that should not count as true anomalies
- one sustained six-sample noisy window that should count as a true anomaly

This is not a real sensor-noise benchmark yet. It isolates the false-positive trade-off
before running the same idea on Raspberry Pi sensor data.

## Policy

The optimized policy is intentionally small:

```text
confirm anomaly only after 2 consecutive threshold crossings
```

This suppresses single-sample spikes, but it can delay detection of real sustained
anomalies.

## Result

| Metric | Threshold only | Hysteresis filter |
| --- | ---: | ---: |
| evaluated samples | 120 | 120 |
| true anomalies | 6 | 6 |
| predicted anomalies | 8 | 5 |
| true positives | 6 | 5 |
| false positives | 2 | 0 |
| false negatives | 0 | 1 |
| precision | 0.7500 | 1.0000 |
| recall | 1.0000 | 0.8333 |
| F1 | 0.8571 | 0.9091 |
| first detected anomaly seq | 95 | 96 |

## Interpretation

The hysteresis filter removed both transient false positives and improved F1 on this
small challenge stream. The cost is one-sample detection delay:

```text
Fewer false alerts, but slower confirmation.
```

The next defensible step is to test this with real sensor data and tune the required
consecutive count against false positives, recall, and detection delay.
