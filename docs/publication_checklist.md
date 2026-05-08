# Publication Checklist

Use this before making the repository public or before pushing a larger update.

## Tracked Content

- Confirm that `git status --short` only shows intentional changes.
- Review `git ls-files` and make sure generated SQLite databases, local dashboard HTML,
  virtual environments, and private sensor captures are not tracked.
- Keep `data/sample.csv` synthetic unless real sensor data has been reviewed for
  privacy and usefulness.

## Secrets and Private Data

Search the repository before publishing. These commands exclude this checklist so the
example patterns do not report themselves:

```bash
rg -n "(ghp_|sk-|AKIA|AIza|xox[baprs]-|BEGIN (RSA|OPENSSH|PRIVATE) KEY|Authorization: Bearer)" . --glob "!docs/publication_checklist.md"
rg -n "(/Users/[^/]+|[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\\.[A-Za-z]{2,})" . --glob "!docs/publication_checklist.md"
```

Expected result for the current benchmark is no project secret, token, credential, or
personal dataset.

## Public Claims

- Do not claim Raspberry Pi latency, CPU, memory, or power results until those
  experiments have been run on the target hardware.
- Keep synthetic-data results labeled as synthetic.
- Keep each improvement paired with its trade-off, especially for adaptive sampling and
  hysteresis filtering.

## Generated Artifacts

These should stay local unless there is a reason to publish a specific artifact:

- `data/*.sqlite`
- `data/*_experiment/`
- `dashboard/index.html`
- `.venv/`

If a screenshot or demo video is added later, regenerate it from the local dashboard
after rerunning the experiments.
