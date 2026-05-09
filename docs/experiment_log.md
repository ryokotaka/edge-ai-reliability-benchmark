# Experiment Log

| Date | Experiment | Result | Notes |
| --- | --- | --- | --- |
| 2026-04-24 | v0 synthetic data skeleton | missing rate 0.0344, p95 latency 132.089 ms, uptime ratio 0.9539 | Default deterministic sample |
| 2026-05-08 | v1 local buffer recovery | baseline recovery loss 120, optimized recovery loss 0, recovered rows 120 | Simulated SQLite write failure for seq 600..719 |
| 2026-05-08 | v2 quantized anomaly scoring | float-like F1 0.9600, quantized-like F1 0.9600, state size 48 bytes -> 6 bytes | Python timing is too small for hardware claims |
| 2026-05-08 | v3 adaptive sampling | sampled rows 1738 -> 1470, estimated inference reduction 15.42%, F1 0.9600 -> 0.8696 | Trade-off: fewer inferences but more missed anomalies |
| 2026-05-08 | v4 batch SQLite writes | insert calls 1800 -> 18, commits 1800 -> 18, elapsed ~5.5 s -> ~67 ms | Timing is machine-dependent; write-call reduction is the stable result |
| 2026-05-08 | v5 hysteresis false-positive filter | false positives 2 -> 0, precision 0.7500 -> 1.0000, recall 1.0000 -> 0.8333 | Trade-off: removes single-sample false alerts but confirms sustained anomalies 1 sample later |
| 2026-05-08 | v6 static dashboard | Generates `dashboard/index.html` from local summary JSON files | No external service or paid API; generated HTML is ignored |
| 2026-05-09 | v7 tiny learned sensor model | float learned F1 1.0000, quantized learned F1 1.0000, state size 104 bytes -> 42 bytes | Standard-library logistic classifier on a fixed chronological synthetic split; test split has 3 anomaly rows |
| 2026-05-09 | v8 tiny model multi-seed stress test | statistical F1 0.8767, float learned F1 0.9487, quantized learned F1 0.9487 across 41 held-out anomalies | 7 deterministic synthetic seeds; still not hardware evidence |
| 2026-05-09 | v9 resource budget gate | quantized tiny model is the only model passing max state 64 B, min F1 0.9000, max false-negative rate 10%, and zero false positives | Proxy edge-style budget; not measured RAM, CPU, latency, or power |
| 2026-05-09 | v10 exported quantized model artifact | loaded artifact F1 1.0000, 0 prediction mismatches, 42-byte model state, 929-byte JSON artifact | Runtime-boundary check; JSON artifact is readable storage, not compact binary deployment |
