from __future__ import annotations

import argparse
import html
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("dashboard/index.html")


@dataclass(frozen=True)
class MetricCard:
    title: str
    before_label: str
    before_value: str
    after_label: str
    after_value: str
    note: str
    tone: str = "neutral"


def load_json(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    return json.loads(path.read_text())


def fmt_number(value: Any, *, digits: int = 4, suffix: str = "") -> str:
    if value is None:
        return "missing"
    if isinstance(value, int):
        return f"{value}{suffix}"
    if isinstance(value, float):
        if abs(value) >= 100:
            return f"{value:.1f}{suffix}"
        return f"{value:.{digits}f}{suffix}"
    return f"{value}{suffix}"


def pct(value: Any) -> str:
    if value is None:
        return "missing"
    return f"{float(value) * 100:.2f}%"


def escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def load_dashboard_data(root: Path = ROOT) -> dict[str, dict[str, Any] | None]:
    return {
        "recovery": load_json(root / "data/recovery_experiment/summary.json"),
        "inference": load_json(root / "data/inference_experiment/summary.json"),
        "tiny_model": load_json(root / "data/tiny_model_experiment/summary.json"),
        "sampling": load_json(root / "data/sampling_experiment/summary.json"),
        "batching": load_json(root / "data/batching_experiment/summary.json"),
        "filtering": load_json(root / "data/filtering_experiment/summary.json"),
    }


def build_metric_cards(data: dict[str, dict[str, Any] | None]) -> list[MetricCard]:
    cards: list[MetricCard] = []
    recovery = data["recovery"]
    if recovery:
        cards.append(
            MetricCard(
                title="Recovery loss",
                before_label="direct write",
                before_value=fmt_number(recovery["baseline"]["recovery_loss"], suffix=" rows"),
                after_label="buffered",
                after_value=fmt_number(recovery["optimized"]["recovery_loss"], suffix=" rows"),
                note=f"{recovery['recovered_rows']} rows recovered after simulated write failure",
                tone="good",
            )
        )

    inference = data["inference"]
    if inference:
        cards.append(
            MetricCard(
                title="Model state",
                before_label="float-like",
                before_value=fmt_number(inference["float32_like"]["model_state_bytes"], suffix=" B"),
                after_label="quantized-like",
                after_value=fmt_number(
                    inference["int8_quantized_like"]["model_state_bytes"],
                    suffix=" B",
                ),
                note=f"F1 stays {fmt_number(inference['int8_quantized_like']['f1'])}",
                tone="good",
            )
        )

    tiny_model = data.get("tiny_model")
    if tiny_model:
        learned = tiny_model["learned_float_like"]
        quantized = tiny_model["learned_quantized_like"]
        cards.append(
            MetricCard(
                title="Tiny model F1",
                before_label="float learned",
                before_value=fmt_number(learned["f1"]),
                after_label="quantized learned",
                after_value=fmt_number(quantized["f1"]),
                note=(
                    f"state {learned['model_state_bytes']} B -> "
                    f"{quantized['model_state_bytes']} B"
                ),
                tone="good" if quantized["f1"] >= learned["f1"] else "tradeoff",
            )
        )

    sampling = data["sampling"]
    if sampling:
        cards.append(
            MetricCard(
                title="Inference work",
                before_label="fixed 1 Hz",
                before_value=fmt_number(sampling["fixed_1hz"]["sampled_count"], suffix=" rows"),
                after_label="adaptive",
                after_value=fmt_number(sampling["adaptive"]["sampled_count"], suffix=" rows"),
                note=f"estimated reduction {pct(sampling['adaptive']['estimated_inference_reduction'])}",
                tone="tradeoff",
            )
        )

    batching = data["batching"]
    if batching:
        cards.append(
            MetricCard(
                title="SQLite commits",
                before_label="per-row",
                before_value=fmt_number(batching["direct_per_row"]["commit_count"]),
                after_label="batched",
                after_value=fmt_number(batching["batched"]["commit_count"]),
                note=f"commit reduction {batching['commit_reduction']}",
                tone="good",
            )
        )

    filtering = data["filtering"]
    if filtering:
        cards.append(
            MetricCard(
                title="False positives",
                before_label="threshold-only",
                before_value=fmt_number(filtering["threshold_only"]["false_positive"]),
                after_label="hysteresis",
                after_value=fmt_number(filtering["hysteresis"]["false_positive"]),
                note=f"detection delay {filtering['detection_delay_samples']} sample",
                tone="tradeoff",
            )
        )

    return cards


def _metric_card_html(card: MetricCard) -> str:
    return f"""
      <article class="metric-card {escape(card.tone)}">
        <div class="metric-title">{escape(card.title)}</div>
        <div class="comparison">
          <div>
            <span>{escape(card.before_label)}</span>
            <strong>{escape(card.before_value)}</strong>
          </div>
          <div>
            <span>{escape(card.after_label)}</span>
            <strong>{escape(card.after_value)}</strong>
          </div>
        </div>
        <p>{escape(card.note)}</p>
      </article>
    """


def _bar(label: str, value: float, max_value: float, tone: str = "blue") -> str:
    width = 0 if max_value <= 0 else max(min(value / max_value, 1), 0) * 100
    return f"""
      <div class="bar-row">
        <span>{escape(label)}</span>
        <div class="bar-track"><div class="bar {escape(tone)}" style="width: {width:.2f}%"></div></div>
        <strong>{fmt_number(value)}</strong>
      </div>
    """


def _missing_section(title: str, command: str) -> str:
    return f"""
      <section class="section muted-section">
        <h2>{escape(title)}</h2>
        <p>Summary data is missing. Run this command, then regenerate the dashboard:</p>
        <pre>{escape(command)}</pre>
      </section>
    """


def _table(headers: Iterable[str], rows: Iterable[Iterable[Any]]) -> str:
    header_html = "".join(f"<th>{escape(header)}</th>" for header in headers)
    row_html = ""
    for row in rows:
        row_html += "<tr>" + "".join(f"<td>{escape(cell)}</td>" for cell in row) + "</tr>"
    return f"<table><thead><tr>{header_html}</tr></thead><tbody>{row_html}</tbody></table>"


def _recovery_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section("Recovery", "python3 scripts/run_recovery_experiment.py")
    baseline = summary["baseline"]
    optimized = summary["optimized"]
    return f"""
      <section class="section">
        <h2>Local Buffer / Checkpoint Recovery</h2>
        <p>Simulated SQLite write failure for seq {summary['failure_start_seq']}..{summary['failure_end_seq'] - 1}.</p>
        {_table(
            ["metric", "direct write", "buffered"],
            [
                ["observed samples", baseline["observed_count"], optimized["observed_count"]],
                ["missing rate", fmt_number(baseline["missing_rate"]), fmt_number(optimized["missing_rate"])],
                ["recovery loss", baseline["recovery_loss"], optimized["recovery_loss"]],
                ["recovered rows", 0, summary["recovered_rows"]],
            ],
        )}
      </section>
    """


def _inference_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section("Lightweight Inference", "python3 scripts/run_inference_experiment.py")
    float_like = summary["float32_like"]
    quantized = summary["int8_quantized_like"]
    return f"""
      <section class="section">
        <h2>Float-like vs Quantized-like Scoring</h2>
        <div class="bars">
          {_bar("float-like state bytes", float_like["model_state_bytes"], float_like["model_state_bytes"])}
          {_bar("quantized-like state bytes", quantized["model_state_bytes"], float_like["model_state_bytes"], "green")}
        </div>
        {_table(
            ["metric", "float-like", "quantized-like"],
            [
                ["evaluated samples", float_like["evaluated_count"], quantized["evaluated_count"]],
                ["precision", fmt_number(float_like["precision"]), fmt_number(quantized["precision"])],
                ["recall", fmt_number(float_like["recall"]), fmt_number(quantized["recall"])],
                ["F1", fmt_number(float_like["f1"]), fmt_number(quantized["f1"])],
                ["state bytes", float_like["model_state_bytes"], quantized["model_state_bytes"]],
            ],
        )}
      </section>
    """


def _tiny_model_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section(
            "Tiny Learned Sensor Model",
            "python3 scripts/run_tiny_model_experiment.py",
        )
    statistical = summary["statistical_scorer"]
    learned = summary["learned_float_like"]
    quantized = summary["learned_quantized_like"]
    max_state = max(learned["model_state_bytes"], quantized["model_state_bytes"], 1)
    return f"""
      <section class="section">
        <h2>Statistical Scorer vs Tiny Learned Sensor Model</h2>
        <p>Fixed chronological split: {summary['train_count']} train rows and {summary['test_count']} test rows.</p>
        <div class="bars">
          {_bar("float learned state bytes", learned["model_state_bytes"], max_state)}
          {_bar("quantized learned state bytes", quantized["model_state_bytes"], max_state, "green")}
        </div>
        {_table(
            ["metric", "statistical", "float learned", "quantized learned"],
            [
                ["evaluated samples", statistical["evaluated_count"], learned["evaluated_count"], quantized["evaluated_count"]],
                ["true positives", statistical["true_positive"], learned["true_positive"], quantized["true_positive"]],
                ["false positives", statistical["false_positive"], learned["false_positive"], quantized["false_positive"]],
                ["false negatives", statistical["false_negative"], learned["false_negative"], quantized["false_negative"]],
                ["precision", fmt_number(statistical["precision"]), fmt_number(learned["precision"]), fmt_number(quantized["precision"])],
                ["recall", fmt_number(statistical["recall"]), fmt_number(learned["recall"]), fmt_number(quantized["recall"])],
                ["F1", fmt_number(statistical["f1"]), fmt_number(learned["f1"]), fmt_number(quantized["f1"])],
                ["state bytes", statistical["model_state_bytes"], learned["model_state_bytes"], quantized["model_state_bytes"]],
            ],
        )}
      </section>
    """


def _sampling_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section("Adaptive Sampling", "python3 scripts/run_sampling_experiment.py")
    fixed = summary["fixed_1hz"]
    adaptive = summary["adaptive"]
    return f"""
      <section class="section">
        <h2>Fixed 1 Hz vs Adaptive Sampling</h2>
        <div class="bars">
          {_bar("fixed sampled rows", fixed["sampled_count"], fixed["sampled_count"])}
          {_bar("adaptive sampled rows", adaptive["sampled_count"], fixed["sampled_count"], "orange")}
        </div>
        {_table(
            ["metric", "fixed 1 Hz", "adaptive"],
            [
                ["sampled rows", fixed["sampled_count"], adaptive["sampled_count"]],
                ["skipped rows", fixed["skipped_count"], adaptive["skipped_count"]],
                ["estimated inference reduction", pct(fixed["estimated_inference_reduction"]), pct(adaptive["estimated_inference_reduction"])],
                ["recall", fmt_number(fixed["recall"]), fmt_number(adaptive["recall"])],
                ["F1", fmt_number(fixed["f1"]), fmt_number(adaptive["f1"])],
            ],
        )}
      </section>
    """


def _batching_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section("Batch SQLite Writes", "python3 scripts/run_batch_write_experiment.py")
    direct = summary["direct_per_row"]
    batched = summary["batched"]
    return f"""
      <section class="section">
        <h2>Direct Writes vs Batched SQLite Writes</h2>
        <div class="bars">
          {_bar("direct commits", direct["commit_count"], direct["commit_count"])}
          {_bar("batched commits", batched["commit_count"], direct["commit_count"], "green")}
        </div>
        {_table(
            ["metric", "direct per-row", "batched"],
            [
                ["rows written", direct["rows_written"], batched["rows_written"]],
                ["insert calls", direct["insert_calls"], batched["insert_calls"]],
                ["commit count", direct["commit_count"], batched["commit_count"]],
                ["rows per commit", fmt_number(direct["rows_per_commit"]), fmt_number(batched["rows_per_commit"])],
                ["elapsed write time", f"~{fmt_number(direct['elapsed_ms'], digits=1)} ms", f"~{fmt_number(batched['elapsed_ms'], digits=1)} ms"],
            ],
        )}
      </section>
    """


def _filtering_section(summary: dict[str, Any] | None) -> str:
    if not summary:
        return _missing_section(
            "Hysteresis Filter",
            "python3 scripts/run_stability_filter_experiment.py",
        )
    raw = summary["threshold_only"]
    filtered = summary["hysteresis"]
    return f"""
      <section class="section">
        <h2>Threshold Alerts vs Hysteresis Filter</h2>
        <div class="bars">
          {_bar("threshold-only false positives", raw["false_positive"], raw["false_positive"])}
          {_bar("hysteresis false positives", filtered["false_positive"], max(raw["false_positive"], 1), "green")}
        </div>
        {_table(
            ["metric", "threshold-only", "hysteresis"],
            [
                ["predicted anomalies", raw["predicted_anomaly_count"], filtered["predicted_anomaly_count"]],
                ["false positives", raw["false_positive"], filtered["false_positive"]],
                ["precision", fmt_number(raw["precision"]), fmt_number(filtered["precision"])],
                ["recall", fmt_number(raw["recall"]), fmt_number(filtered["recall"])],
                ["F1", fmt_number(raw["f1"]), fmt_number(filtered["f1"])],
                ["first detected anomaly seq", raw["first_detected_anomaly_seq"], filtered["first_detected_anomaly_seq"]],
            ],
        )}
      </section>
    """


def build_dashboard_html(root: Path = ROOT) -> str:
    data = load_dashboard_data(root)
    cards = build_metric_cards(data)
    generated_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    cards_html = "\n".join(_metric_card_html(card) for card in cards)
    if not cards_html:
        cards_html = """
          <article class="metric-card neutral">
            <div class="metric-title">No experiment summaries found</div>
            <p>Run the Quick Start commands, then regenerate this dashboard.</p>
          </article>
        """

    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Edge AI Reliability Benchmark Dashboard</title>
  <style>
    :root {{
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #182230;
      --muted: #667085;
      --line: #d6dde7;
      --blue: #2563eb;
      --green: #148a4a;
      --orange: #c56a00;
      --red: #c2410c;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background: var(--bg);
      color: var(--ink);
    }}
    main {{ width: min(1180px, calc(100vw - 32px)); margin: 28px auto 48px; }}
    header {{ margin-bottom: 22px; }}
    h1 {{ font-size: 30px; margin: 0 0 8px; letter-spacing: 0; }}
    h2 {{ font-size: 20px; margin: 0 0 10px; letter-spacing: 0; }}
    p {{ color: var(--muted); line-height: 1.65; }}
    .meta {{ color: var(--muted); font-size: 14px; }}
    .metrics-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 12px;
      margin: 18px 0 20px;
    }}
    .metric-card, .section {{
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 16px;
    }}
    .metric-card.good {{ border-top: 4px solid var(--green); }}
    .metric-card.tradeoff {{ border-top: 4px solid var(--orange); }}
    .metric-card.neutral {{ border-top: 4px solid var(--blue); }}
    .metric-title {{ color: var(--muted); font-size: 13px; font-weight: 700; text-transform: uppercase; }}
    .comparison {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 10px;
      margin-top: 12px;
    }}
    .comparison span {{ display: block; color: var(--muted); font-size: 12px; }}
    .comparison strong {{ display: block; font-size: 24px; margin-top: 2px; }}
    .sections {{ display: grid; gap: 14px; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 12px; font-size: 14px; }}
    th, td {{ border-bottom: 1px solid var(--line); padding: 10px 8px; text-align: right; }}
    th:first-child, td:first-child {{ text-align: left; }}
    th {{ color: var(--muted); font-weight: 700; }}
    .bars {{ display: grid; gap: 8px; margin: 12px 0; }}
    .bar-row {{
      display: grid;
      grid-template-columns: minmax(170px, 1fr) 2fr 80px;
      gap: 10px;
      align-items: center;
      font-size: 14px;
    }}
    .bar-row span {{ color: var(--muted); }}
    .bar-track {{ height: 10px; background: #eef2f7; border-radius: 999px; overflow: hidden; }}
    .bar {{ height: 100%; background: var(--blue); }}
    .bar.green {{ background: var(--green); }}
    .bar.orange {{ background: var(--orange); }}
    pre {{
      overflow-x: auto;
      background: #101828;
      color: #e5e7eb;
      padding: 12px;
      border-radius: 8px;
    }}
    @media (max-width: 720px) {{
      .comparison {{ grid-template-columns: 1fr; }}
      .bar-row {{ grid-template-columns: 1fr; }}
      th, td {{ font-size: 13px; }}
    }}
  </style>
</head>
<body>
  <main>
    <header>
      <h1>Edge AI Reliability Benchmark Dashboard</h1>
      <p>Local summary of reliability, lightweight inference, tiny learned model, adaptive sampling, SQLite batching, and false-positive filtering experiments.</p>
      <div class="meta">Generated at {escape(generated_at)}</div>
    </header>

    <section class="metrics-grid">
      {cards_html}
    </section>

    <section class="sections">
      {_recovery_section(data["recovery"])}
      {_inference_section(data["inference"])}
      {_tiny_model_section(data["tiny_model"])}
      {_sampling_section(data["sampling"])}
      {_batching_section(data["batching"])}
      {_filtering_section(data["filtering"])}
    </section>
  </main>
</body>
</html>
"""


def write_dashboard(output_path: Path, *, root: Path = ROOT) -> Path:
    resolved = output_path if output_path.is_absolute() else root / output_path
    resolved.parent.mkdir(parents=True, exist_ok=True)
    resolved.write_text(build_dashboard_html(root), encoding="utf-8")
    return resolved


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate a static HTML dashboard from local experiment summaries."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    output_path = write_dashboard(args.output)
    print(f"wrote_dashboard={output_path}")


if __name__ == "__main__":
    main()
