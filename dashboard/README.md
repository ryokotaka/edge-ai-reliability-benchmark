# Dashboard

This dashboard is a dependency-free static HTML report generated from local experiment
summary files.

Generate all experiment summaries first:

```bash
python3 scripts/generate_synthetic_data.py
python3 -m edge_agent.storage data/sample.csv data/readings.sqlite
python3 scripts/run_recovery_experiment.py
python3 scripts/run_inference_experiment.py
python3 scripts/run_sampling_experiment.py
python3 scripts/run_batch_write_experiment.py
python3 scripts/run_stability_filter_experiment.py
```

Then generate the dashboard:

```bash
python3 dashboard/app.py
```

Open `dashboard/index.html` in a browser.
