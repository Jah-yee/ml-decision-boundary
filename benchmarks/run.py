"""
Standardized benchmark harness for ml-decision-boundary

Supports:
  - Full benchmark suite (all models × all datasets)
  - Quick smoke test (single model + dataset)
  - Structured JSON output for CI/regression tracking
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Ensure project root in path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from main import generate_dataset, train_model, run_experiment, run_all_experiments, save_results

# ── Configuration ──────────────────────────────────────────────────────────────

MODELS = {
    "SVM": [
        {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
        {"kernel": "rbf", "C": 10.0, "gamma": "scale"},
        {"kernel": "linear", "C": 1.0},
    ],
    "LR": [
        {"C": 1.0},
    ],
    "Tree": [
        {"max_depth": 3},
        {"max_depth": 10},
    ],
    "RF": [
        {"n_estimators": 50, "max_depth": 5},
        {"n_estimators": 100, "max_depth": 10},
    ],
    "KNN": [
        {"n_neighbors": 3},
        {"n_neighbors": 7},
        {"n_neighbors": 15},
    ],
    "MLP": [
        {"hidden_layer_sizes": (50,), "alpha": 0.001},
        {"hidden_layer_sizes": (100, 50), "alpha": 0.001},
    ],
}

DATASETS = ["circles", "moons", "blobs", "xor"]

# Thresholds for regression detection (accuracy must be >= this)
ACCURACY_THRESHOLDS = {
    "circles": 0.70,
    "moons": 0.70,
    "blobs": 0.90,
    "xor": 0.60,
}


def run_quick_benchmark() -> dict:
    """Run a single smoke test: SVM on circles, to verify the harness is functional."""
    dataset_name = "circles"
    model_type = "SVM"
    params = {"kernel": "rbf", "C": 1.0, "gamma": "scale"}

    t0 = time.perf_counter()
    result = run_experiment(dataset_name, model_type, params)
    elapsed = time.perf_counter() - t0

    return {
        "smoke_test": True,
        "dataset": dataset_name,
        "model": model_type,
        "params": params,
        "accuracy": result.accuracy,
        "train_time": result.train_time,
        "wall_time": elapsed,
        "passed": result.accuracy >= ACCURACY_THRESHOLDS[dataset_name],
    }


def run_full_benchmark() -> list:
    """Run all model × dataset combinations."""
    results = []
    for dataset_name in DATASETS:
        for model_type, param_list in MODELS.items():
            for params in param_list:
                try:
                    result = run_experiment(dataset_name, model_type, params)
                    results.append({
                        "dataset": dataset_name,
                        "model": model_type,
                        "params": params,
                        "accuracy": result.accuracy,
                        "train_time": result.train_time,
                        "passed": result.accuracy >= ACCURACY_THRESHOLDS.get(dataset_name, 0.0),
                    })
                except Exception as e:
                    results.append({
                        "dataset": dataset_name,
                        "model": model_type,
                        "params": params,
                        "error": str(e),
                        "passed": False,
                    })
    return results


def generate_summary(results: list, smoke_test: bool = False) -> dict:
    """Compute aggregate stats from benchmark results."""
    if smoke_test:
        r = results[0]
        return {
            "smoke_test": True,
            "dataset": r["dataset"],
            "model": r["model"],
            "accuracy": r["accuracy"],
            "train_time": r["train_time"],
            "wall_time": r["wall_time"],
            "passed": r["passed"],
            "threshold": ACCURACY_THRESHOLDS[r["dataset"]],
        }

    total = len(results)
    passed = sum(1 for r in results if r.get("passed", False))
    errors = sum(1 for r in results if "error" in r)
    accuracies = [r["accuracy"] for r in results if "accuracy" in r]
    times = [r["train_time"] for r in results if "train_time" in r]

    return {
        "smoke_test": False,
        "total_experiments": total,
        "passed": passed,
        "failed": total - passed,
        "errors": errors,
        "best_accuracy": max(accuracies) if accuracies else None,
        "worst_accuracy": min(accuracies) if accuracies else None,
        "avg_accuracy": sum(accuracies) / len(accuracies) if accuracies else None,
        "avg_train_time": sum(times) / len(times) if times else None,
        "by_dataset": {
            ds: {
                "count": sum(1 for r in results if r.get("dataset") == ds),
                "avg_acc": sum(r["accuracy"] for r in results if r.get("dataset") == ds and "accuracy" in r) /
                            max(1, sum(1 for r in results if r.get("dataset") == ds and "accuracy" in r)),
            }
            for ds in DATASETS
        },
    }


def write_report(output_dir: Path, results: list, summary: dict) -> tuple:
    """Write JSON + MD reports."""
    output_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d")
    json_path = output_dir / f"{ts}.json"
    md_path = output_dir / f"{ts}.md"

    with open(json_path, "w") as f:
        json.dump({"results": results, "summary": summary, "timestamp": datetime.now().isoformat()}, f, indent=2)

    # Markdown summary
    is_smoke = summary.get("smoke_test", False)
    md_lines = [
        f"# benchmarks/report — {ts}",
        "",
        f"**Mode**: {'Quick smoke' if is_smoke else 'Full suite'}",
        "",
    ]
    if is_smoke:
        r = summary
        md_lines.extend([
            f"| Field | Value |",
            f"|-------|-------|",
            f"| Dataset | {r['dataset']} |",
            f"| Model | {r['model']} |",
            f"| Accuracy | {r['accuracy']:.4f} |",
            f"| Train time | {r['train_time']:.4f}s |",
            f"| Wall time | {r['wall_time']:.4f}s |",
            f"| Threshold | {r['threshold']:.4f} |",
            f"| Passed | {'✅' if r['passed'] else '❌'} |",
        ])
    else:
        s = summary
        md_lines.extend([
            f"| Metric | Value |",
            f"|-------|-------|",
            f"| Total experiments | {s['total_experiments']} |",
            f"| Passed | {s['passed']} |",
            f"| Failed | {s['failed']} |",
            f"| Errors | {s['errors']} |",
            f"| Best accuracy | {s['best_accuracy']:.4f} |",
            f"| Worst accuracy | {s['worst_accuracy']:.4f} |",
            f"| Avg accuracy | {s['avg_accuracy']:.4f} |",
            f"| Avg train time | {s['avg_train_time']:.4f}s |",
            "",
            "## Results table",
            "",
            "| Dataset | Model | Accuracy | Train time | Passed |",
            "|---------|-------|----------|------------|--------|",
        ])
        for r in results:
            acc = f"{r['accuracy']:.4f}" if "accuracy" in r else "ERROR"
            t = f"{r['train_time']:.4f}s" if "train_time" in r else "—"
            md_lines.append(f"| {r['dataset']} | {r['model']} | {acc} | {t} | {'✅' if r.get('passed') else '❌'} |")

    md_path.write_text("\n".join(md_lines))
    return str(json_path), str(md_path)


def run_benchmarks(quick: bool = False) -> dict:
    """Main entry point: run benchmarks and return summary dict."""
    raw_results = run_quick_benchmark() if quick else run_full_benchmark()
    # Normalize to list
    results = [raw_results] if isinstance(raw_results, dict) else raw_results
    summary = generate_summary(results, smoke_test=quick)
    report_dir = Path(__file__).parent / "reports"
    json_path, md_path = write_report(report_dir, results, summary)
    summary["json_report"] = json_path
    summary["md_report"] = md_path
    return summary


def main():
    parser = argparse.ArgumentParser(description="ml-decision-boundary benchmark harness")
    parser.add_argument("--quick", action="store_true", help="Run only a single smoke test")
    parser.add_argument("--report", action="store_true", help="Generate report (default on)")
    parser.add_argument("--no-report", action="store_true", help="Skip report generation")
    args = parser.parse_args()

    if args.quick:
        print("🏃 Running quick smoke test...")
        summary = run_benchmarks(quick=True)
        print(f"  Dataset: {summary['dataset']}, Model: {summary['model']}")
        print(f"  Accuracy: {summary['accuracy']:.4f} | Threshold: {summary['threshold']:.4f}")
        print(f"  {'✅ PASSED' if summary['passed'] else '❌ FAILED'}")
    else:
        print("🎯 Running full benchmark suite...")
        summary = run_benchmarks(quick=False)
        print(f"  Total: {summary['total_experiments']} | Passed: {summary['passed']} | Failed: {summary['failed']}")
        print(f"  Avg accuracy: {summary['avg_accuracy']:.4f} | Avg train time: {summary['avg_train_time']:.4f}s")
        print(f"  Reports: {summary['json_report']} + {summary['md_report']}")

    return 0 if summary["passed"] > 0 else 1


if __name__ == "__main__":
    sys.exit(main())