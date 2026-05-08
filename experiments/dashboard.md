# Static Dashboard

## Scope

The dashboard is a local static HTML report. It reads experiment summary JSON files
from `data/*_experiment/summary.json` and writes `dashboard/index.html`.

It does not use a cloud backend, paid API, JavaScript framework, or Streamlit
dependency. The generated HTML is ignored by git because it is a local artifact.

## Inputs

| Experiment | Summary path |
| --- | --- |
| recovery | `data/recovery_experiment/summary.json` |
| inference | `data/inference_experiment/summary.json` |
| adaptive sampling | `data/sampling_experiment/summary.json` |
| batch writes | `data/batching_experiment/summary.json` |
| hysteresis filter | `data/filtering_experiment/summary.json` |

## Usage

```bash
python3 scripts/generate_synthetic_data.py
python3 -m edge_agent.storage data/sample.csv data/readings.sqlite
python3 scripts/run_recovery_experiment.py
python3 scripts/run_inference_experiment.py
python3 scripts/run_sampling_experiment.py
python3 scripts/run_batch_write_experiment.py
python3 scripts/run_stability_filter_experiment.py
python3 dashboard/app.py
```

Then open `dashboard/index.html`.

## Interpretation

The dashboard is not a new benchmark result. It is a viewing layer that makes the
existing before / after evidence easier to scan:

- recovery loss: direct write vs buffered recovery
- model state: float-like vs quantized-like scoring
- inference work: fixed 1 Hz vs adaptive sampling
- SQLite commits: per-row writes vs batch writes
- false positives: threshold-only vs hysteresis filtering
