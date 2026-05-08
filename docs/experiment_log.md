# Experiment Log

| Date | Experiment | Result | Notes |
| --- | --- | --- | --- |
| 2026-04-24 | v0 synthetic data skeleton | missing rate 0.0344, p95 latency 132.089 ms, uptime ratio 0.9539 | Default deterministic sample |
| 2026-05-08 | v1 local buffer recovery | baseline recovery loss 120, optimized recovery loss 0, recovered rows 120 | Simulated SQLite write failure for seq 600..719 |
| 2026-05-08 | v2 quantized anomaly scoring | float-like F1 0.9600, quantized-like F1 0.9600, state size 48 bytes -> 6 bytes | Python timing is too small for hardware claims |
| 2026-05-08 | v3 adaptive sampling | sampled rows 1738 -> 1470, estimated inference reduction 15.42%, F1 0.9600 -> 0.8696 | Trade-off: fewer inferences but more missed anomalies |
| 2026-05-08 | v4 batch SQLite writes | insert calls 1800 -> 18, commits 1800 -> 18, elapsed ~5.5 s -> ~67 ms | Timing is machine-dependent; write-call reduction is the stable result |
| 2026-05-08 | v5 hysteresis false-positive filter | false positives 2 -> 0, precision 0.7500 -> 1.0000, recall 1.0000 -> 0.8333 | Trade-off: removes single-sample false alerts but confirms sustained anomalies 1 sample later |
