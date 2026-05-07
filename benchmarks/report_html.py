"""
HTML report generator for benchmark history.
Reads all JSON reports from benchmarks/reports/ and produces a standalone HTML file
with trend charts and summary tables.
"""

import json
import sys
from datetime import datetime
from pathlib import Path

# Ensure project root in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np


def load_all_reports(reports_dir: Path) -> list:
    """Load all JSON benchmark reports, sorted by date."""
    reports = []
    for p in sorted(reports_dir.glob("????-??-??.json")):
        try:
            data = json.loads(p.read_text())
            date_str = p.stem  # e.g. "2026-04-28"
            data["_date"] = datetime.strptime(date_str, "%Y-%m-%d")
            reports.append(data)
        except Exception:
            pass
    return reports


def build_trend_data(reports: list) -> dict:
    """Extract per-(dataset, model) accuracy and train_time time series."""
    full_reports = [r for r in reports if not r.get("summary", {}).get("smoke_test", False)]
    smoke_reports = [r for r in reports if r.get("summary", {}).get("smoke_test", False)]

    by_dm = {}
    for rep in full_reports:
        for r in rep.get("results", []):
            key = (r["dataset"], r["model"])
            if key not in by_dm:
                by_dm[key] = {"dates": [], "accuracies": [], "train_times": []}
            by_dm[key]["dates"].append(rep["_date"])
            by_dm[key]["accuracies"].append(r["accuracy"])
            by_dm[key]["train_times"].append(r.get("train_time", 0))

    summary_trend = []
    for rep in full_reports:
        s = rep.get("summary", {})
        summary_trend.append({
            "date": rep["_date"],
            "total": s.get("total_experiments", 0),
            "passed": s.get("passed", 0),
            "avg_acc": s.get("avg_accuracy", 0),
            "avg_train_time": s.get("avg_train_time", 0),
        })

    return {
        "full_reports": full_reports,
        "smoke_reports": smoke_reports,
        "by_dm": by_dm,
        "summary_trend": summary_trend,
    }


def plot_accuracy_trend(by_dm: dict, output_path: Path):
    """Line chart: accuracy over time for each (dataset, model) pair."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    datasets = ["circles", "moons", "blobs", "xor"]

    colors = {
        "SVM": "#1f77b4", "LR": "#ff7f0e", "Tree": "#2ca02c",
        "RF": "#d62728", "KNN": "#9467bd", "MLP": "#8c564b",
    }

    for idx, ds in enumerate(datasets):
        ax = axes[idx]
        for (dataset, model), series in by_dm.items():
            if dataset != ds:
                continue
            dates = matplotlib.dates.date2num(series["dates"])
            ax.plot_date(dates, series["accuracies"], label=model,
                         color=colors.get(model, "#333"), fmt="o", markersize=4)
        ax.set_title(f"Accuracy — {ds}", fontsize=12, fontweight="bold")
        ax.set_ylabel("Accuracy")
        ax.set_ylim(0.0, 1.05)
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3)
        ax.axhline(0.7, color="red", linestyle="--", alpha=0.4)
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.tick_params(axis="x", rotation=30)

    plt.suptitle("Model Accuracy Trend by Dataset", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_train_time_trend(by_dm: dict, output_path: Path):
    """Line chart: training time over time (log scale)."""
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    axes = axes.flatten()
    datasets = ["circles", "moons", "blobs", "xor"]

    colors = {
        "SVM": "#1f77b4", "LR": "#ff7f0e", "Tree": "#2ca02c",
        "RF": "#d62728", "KNN": "#9467bd", "MLP": "#8c564b",
    }

    for idx, ds in enumerate(datasets):
        ax = axes[idx]
        for (dataset, model), series in by_dm.items():
            if dataset != ds:
                continue
            dates = matplotlib.dates.date2num(series["dates"])
            ax.plot_date(dates, series["train_times"], label=model,
                         color=colors.get(model, "#333"), fmt="o", markersize=4)
        ax.set_title(f"Train Time — {ds}", fontsize=12, fontweight="bold")
        ax.set_ylabel("Train Time (s)")
        ax.set_yscale("log")
        ax.legend(fontsize=8)
        ax.grid(True, alpha=0.3, which="both")
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%m-%d"))
        ax.tick_params(axis="x", rotation=30)

    plt.suptitle("Training Time Trend by Dataset (log scale)", fontsize=14, fontweight="bold")
    plt.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def plot_summary_trend(summary_trend: list, output_path: Path):
    """Bar + line combo: pass rate and avg accuracy over time."""
    if not summary_trend:
        return

    dates = [s["date"] for s in summary_trend]
    pass_rates = [s["passed"] / max(1, s["total"]) * 100 for s in summary_trend]
    avg_accs = [s["avg_acc"] * 100 for s in summary_trend]

    fig, ax1 = plt.subplots(figsize=(12, 5))
    num_dates = len(dates)
    x = np.arange(num_dates)
    bars = ax1.bar(x, pass_rates, color="#2ca02c", alpha=0.7, label="Pass Rate (%)")
    ax1.set_ylabel("Pass Rate (%)")
    ax1.set_ylim(0, 110)
    ax1.set_xticks(x)
    ax1.set_xticklabels([d.strftime("%m-%d") for d in dates], rotation=30)
    ax1.grid(True, axis="y", alpha=0.3)

    ax2 = ax1.twinx()
    ax2.plot(x, avg_accs, color="#1f77b4", marker="o", linewidth=2, label="Avg Accuracy (%)")
    ax2.set_ylabel("Avg Accuracy (%)")
    ax2.set_ylim(0, 110)

    for bar, rate in zip(bars, pass_rates):
        ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 1,
                 f"{rate:.0f}%", ha="center", va="bottom", fontsize=8)

    plt.title("Benchmark Suite Summary Trend", fontsize=13, fontweight="bold")
    fig.legend(loc="upper right", bbox_to_anchor=(0.88, 0.88))
    plt.tight_layout()
    fig.savefig(output_path, dpi=120, bbox_inches="tight")
    plt.close(fig)


def generate_html(reports: list, output_path: Path, trend_data: dict, ts: str):
    """Write the full HTML report."""
    full_reports = trend_data["full_reports"]
    summary_trend = trend_data["summary_trend"]

    if full_reports:
        latest = full_reports[-1]
        latest_date = latest["_date"].strftime("%Y-%m-%d")
        results = latest.get("results", [])
    else:
        latest_date = "N/A"
        results = []

    summary_cards_html = ""
    if summary_trend:
        last = summary_trend[-1]
        prev = summary_trend[-2] if len(summary_trend) >= 2 else last
        delta_acc = (last["avg_acc"] - prev["avg_acc"]) * 100
        delta_pass = last["passed"] - prev["passed"]
        summary_cards_html = f"""
        <div class="cards">
          <div class="card">
            <div class="card-value">{last['passed']}/{last['total']}</div>
            <div class="card-label">Experiments Passed (Latest)</div>
          </div>
          <div class="card">
            <div class="card-value">{last['avg_acc']:.1%}</div>
            <div class="card-label">Avg Accuracy (Latest)</div>
          </div>
          <div class="card">
            <div class="card-value" style="color:{'green' if delta_acc >= 0 else 'red'}">
              {'+' if delta_acc >= 0 else ''}{delta_acc:.1f}%
            </div>
            <div class="card-label">Accuracy Δ vs Prior</div>
          </div>
          <div class="card">
            <div class="card-value" style="color:{'green' if delta_pass >= 0 else 'red'}">
              {'+' if delta_pass >= 0 else ''}{delta_pass}
            </div>
            <div class="card-label">Pass Count Δ vs Prior</div>
          </div>
        </div>
        """

    rows_html = ""
    for r in sorted(results, key=lambda x: (x["dataset"], x["model"])):
        status = "✅" if r.get("passed") else "❌"
        acc = f"{r['accuracy']:.4f}"
        t = f"{r.get('train_time', 0):.4f}s"
        rows_html += f"""
        <tr>
          <td>{r['dataset']}</td>
          <td><code>{r['model']}</code></td>
          <td>{acc}</td>
          <td>{t}</td>
          <td>{status}</td>
        </tr>"""

    all_reports_sorted = sorted(reports, key=lambda r: r["_date"], reverse=True)
    history_rows = ""
    for rep in all_reports_sorted:
        s = rep.get("summary", {})
        is_smoke = s.get("smoke_test", False)
        date_str = rep["_date"].strftime("%Y-%m-%d")
        if is_smoke:
            history_rows += f"<tr><td>{date_str}</td><td>Smoke</td><td>{s.get('dataset','?')}</td><td>{s.get('model','?')}</td><td>{s.get('accuracy',0):.4f}</td><td>—</td><td>{'✅' if s.get('passed') else '❌'}</td></tr>"
        else:
            history_rows += f"<tr><td>{date_str}</td><td>Full</td><td>{s.get('total_experiments',0)}</td><td>{s.get('passed',0)}</td><td>{s.get('avg_accuracy',0):.4f}</td><td>{s.get('avg_train_time',0):.4f}s</td><td>{'✅' if s.get('passed',0) == s.get('total_experiments',0) else '⚠️'}</td></tr>"

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Benchmark Report — ml-decision-boundary</title>
<style>
  :root {{
    --bg: #0f1117;
    --surface: #1a1d27;
    --border: #2a2d3a;
    --text: #e0e3f0;
    --muted: #8b8fa8;
    --accent: #61afef;
    --green: #98c379;
    --red: #e06c75;
    --yellow: #e5c07b;
    font-size: 14px;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 2rem 1rem; }}
  header {{ margin-bottom: 2rem; }}
  h1 {{ color: var(--accent); font-size: 1.8rem; }}
  h2 {{ color: var(--text); margin: 2rem 0 1rem; border-bottom: 1px solid var(--border); padding-bottom: 0.5rem; font-size: 1.2rem; }}
  .meta {{ color: var(--muted); font-size: 0.85rem; }}
  .cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 1rem; margin-bottom: 1.5rem; }}
  .card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem; text-align: center; }}
  .card-value {{ font-size: 1.6rem; font-weight: 700; color: var(--accent); }}
  .card-label {{ font-size: 0.75rem; color: var(--muted); margin-top: 0.25rem; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 1rem; }}
  th, td {{ padding: 0.5rem 0.75rem; text-align: left; border-bottom: 1px solid var(--border); }}
  th {{ background: var(--surface); color: var(--accent); font-weight: 600; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.05em; }}
  tr:hover td {{ background: rgba(97,175,239,0.05); }}
  code {{ background: var(--surface); padding: 0.1em 0.4em; border-radius: 4px; font-size: 0.85em; }}
  img {{ max-width: 100%; border-radius: 8px; border: 1px solid var(--border); }}
  .chart-full {{ margin-bottom: 1rem; }}
  @media (max-width: 768px) {{ .chart-section {{ grid-template-columns: 1fr; }} }}
</style>
</head>
<body>
<div class="container">
<header>
  <h1>📊 Benchmark Report — ml-decision-boundary</h1>
  <p class="meta">Latest run: <strong>{latest_date}</strong> &nbsp;|&nbsp; Total reports: {len(reports)} &nbsp;|&nbsp; Full suite: {len(full_reports)} &nbsp;|&nbsp; Smoke: {len(trend_data['smoke_reports'])}</p>
</header>

<h2>📈 Summary Cards</h2>
{summary_cards_html or '<p class="meta">No full-suite data available yet.</p>'}

<h2>📋 Latest Results ({latest_date})</h2>
<table>
  <thead><tr><th>Dataset</th><th>Model</th><th>Accuracy</th><th>Train Time</th><th>Status</th></tr></thead>
  <tbody>
  {rows_html or '<tr><td colspan="5" style="text-align:center;color:var(--muted)">No data</td></tr>'}
  </tbody>
</table>

<h2>📉 Accuracy Trend by Dataset</h2>
<div class="chart-full">
  <img src="{ts}_accuracy_trend.png" alt="Accuracy trend" loading="lazy">
</div>

<h2>⏱ Training Time Trend (log scale)</h2>
<div class="chart-full">
  <img src="{ts}_train_time_trend.png" alt="Train time trend" loading="lazy">
</div>

<h2>📊 Suite Summary Trend</h2>
<div class="chart-full">
  <img src="{ts}_summary_trend.png" alt="Summary trend" loading="lazy">
</div>

<h2>📁 Report History</h2>
<table>
  <thead><tr><th>Date</th><th>Type</th><th>Experiments</th><th>Passed</th><th>Avg Accuracy</th><th>Avg Train Time</th><th>Status</th></tr></thead>
  <tbody>
  {history_rows or '<tr><td colspan="7" style="text-align:center;color:var(--muted)">No data</td></tr>'}
  </tbody>
</table>

<footer style="margin-top:3rem;padding-top:1rem;border-top:1px solid var(--border);color:var(--muted);font-size:0.8rem">
  <p>Generated by ml-decision-boundary benchmark HTML reporter &nbsp;|&nbsp; <code>python -m benchmarks.report_html</code></p>
</footer>
</div>
</body>
</html>"""
    output_path.write_text(html)


def generate_report(reports_dir: Path, output_dir: Path) -> str:
    """Main entry point: generate HTML report and save to output_dir."""
    reports_dir = Path(reports_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    reports = load_all_reports(reports_dir)
    trend_data = build_trend_data(reports)

    ts = datetime.now().strftime("%Y-%m-%d")
    html_path = output_dir / f"{ts}.html"
    acc_chart_path = output_dir / f"{ts}_accuracy_trend.png"
    time_chart_path = output_dir / f"{ts}_train_time_trend.png"
    summary_chart_path = output_dir / f"{ts}_summary_trend.png"

    print("  Generating charts...")
    if trend_data["by_dm"]:
        plot_accuracy_trend(trend_data["by_dm"], acc_chart_path)
        plot_train_time_trend(trend_data["by_dm"], time_chart_path)
    if trend_data["summary_trend"]:
        plot_summary_trend(trend_data["summary_trend"], summary_chart_path)

    print("  Writing HTML report...")
    generate_html(reports, html_path, trend_data, ts)

    print(f"  ✅ HTML report: {html_path}")
    print(f"  ✅ Accuracy chart: {acc_chart_path}")
    print(f"  ✅ Train time chart: {time_chart_path}")
    print(f"  ✅ Summary chart: {summary_chart_path}")
    return str(html_path)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate HTML benchmark report")
    parser.add_argument("--reports-dir", default=str(Path(__file__).parent / "reports"),
                        help="Directory containing JSON report files")
    parser.add_argument("--output-dir", default=str(Path(__file__).parent / "reports"),
                        help="Output directory for HTML report")
    args = parser.parse_args()
    generate_report(args.reports_dir, args.output_dir)
