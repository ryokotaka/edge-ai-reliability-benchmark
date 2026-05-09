# Exported Quantized Model Artifact

## Scope

This experiment checks whether the selected quantized tiny model can be moved from
"trained in memory" to a small saved runtime artifact.

It is not hardware deployment yet. It does not claim compact binary size, RAM usage,
CPU cost, latency, or power consumption on a target device. The goal is narrower:
prove that inference can run from exported quantized model state without retraining.

## Method

1. Load the default deterministic synthetic CSV.
2. Keep the fixed chronological split: 70% train, 30% test.
3. Train the float tiny model on the train rows.
4. Convert it to the quantized-like tiny model.
5. Export only the quantized runtime state to JSON.
6. Load the JSON artifact back into a `QuantizedTinyModel`.
7. Compare loaded-artifact predictions against the in-memory quantized model.

The JSON artifact is intentionally readable for review. Its file size is larger than
the model state because it includes field names, formatting, and metadata.

## Result

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

Artifact details:

| Item | Value |
| --- | ---: |
| artifact version | 1 |
| model type | `quantized_tiny_sensor_model` |
| runtime state size | 42 bytes |
| JSON artifact file size | 929 bytes |

## Interpretation

The loaded artifact matches the in-memory quantized model on the held-out split. That
makes the next deployment boundary clearer: training and quantization can happen
offline, while runtime inference only needs the saved quantized state.

The result is still synthetic and laptop-local. It should be described as a
deployment-shaped runtime check, not as proof of Raspberry Pi performance.
