# Dashboard

This dashboard is a dependency-free static HTML report generated from local experiment
summary files.

It is meant to make the benchmark easier to scan when showing the project to someone:
one page compares recovery loss, inference state size, adaptive sampling, SQLite commit
count, and false-positive filtering.

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

Notes:

- The generated HTML is a local artifact and is ignored by git.
- The dashboard does not call an external API or send data anywhere.
- If a future screenshot or demo video is added, regenerate it from this local HTML so
  it reflects tracked code and synthetic data.
