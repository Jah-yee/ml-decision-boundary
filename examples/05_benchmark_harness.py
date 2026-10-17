#!/usr/bin/env python3
"""
05_benchmark_harness.py — 运行 benchmark 并解读报告

目标：展示如何运行 benchmark harness、解读回归检测结果。
依赖： benchmarks.run（已在项目中）
输出：benchmarks/reports/YYYY-MM-DD.md
运行：
  python examples/05_benchmark_harness.py --quick   # 快速冒烟（推荐先跑这个）
  python examples/05_benchmark_harness.py          # 完整 suite（较长）

本例使用 --quick 模式：单数据集 + 4 个核心模型，30 秒内完成。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import argparse
import json
import time
from datetime import datetime
from pathlib import Path

from sklearn.datasets import make_circles, make_moons, make_blobs
from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split

# ── Benchmark 配置（缩减版，快速验证）──────────────────────────────────────────

QUICK_MODELS = {
    "SVM": {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
    "Tree": {"max_depth": 5},
    "KNN": {"n_neighbors": 7},
    "RF": {"n_estimators": 50, "max_depth": 5},
}

QUICK_DATASETS = {
    "circles": lambda: make_circles(n_samples=300, noise=0.2, random_state=42),
    "moons": lambda: make_moons(n_samples=300, noise=0.2, random_state=42),
}


def run_quick_benchmark() -> dict:
    """
    Run a quick benchmark: 2 datasets × 4 models = 8 experiments.
    Returns a dict summary for reporting.
    """
    results = []
    started_at = time.time()

    for ds_name, ds_fn in QUICK_DATASETS.items():
        X, y = ds_fn()
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        for model_name, params in QUICK_MODELS.items():
            try:
                model = _build_model(model_name, params)
                model.fit(X_train, y_train)
                train_acc = model.score(X_train, y_train)
                test_acc = model.score(X_test, y_test)

                results.append({
                    "model": model_name,
                    "dataset": ds_name,
                    "params": params,
                    "train_accuracy": round(train_acc, 4),
                    "test_accuracy": round(test_acc, 4),
                    "status": "passed",
                })
            except Exception as e:
                results.append({
                    "model": model_name,
                    "dataset": ds_name,
                    "params": params,
                    "status": "failed",
                    "error": str(e),
                })

    duration = time.time() - started_at
    passed = sum(1 for r in results if r["status"] == "passed")
    failed = sum(1 for r in results for _ in [1] if r["status"] == "failed")

    return {
        "timestamp": datetime.now().isoformat(),
        "duration_seconds": round(duration, 2),
        "mode": "quick",
        "total_experiments": len(results),
        "passed": passed,
        "failed": failed,
        "regressions": 0,  # 无 historical data 无法检测回归
        "results": results,
    }


def _build_model(name: str, params: dict):
    """Build sklearn model by name + params."""
    if name == "SVM":
        return SVC(**params, random_state=42)
    elif name == "Tree":
        return DecisionTreeClassifier(**params, random_state=42)
    elif name == "KNN":
        return KNeighborsClassifier(**params)
    elif name == "RF":
        return RandomForestClassifier(**params, random_state=42)
    else:
        raise ValueError(f"Unknown model: {name}")


def print_summary(report: dict):
    """Pretty-print benchmark summary to console."""
    print()
    print("═" * 60)
    print(f"  Benchmark Report — {report['mode'].upper()}")
    print("═" * 60)
    print(f"  时间: {report['timestamp']}")
    print(f"  耗时: {report['duration_seconds']:.1f}s")
    print(f"  实验: {report['passed']}/{report['total_experiments']} passed", end="")
    if report['failed'] > 0:
        print(f", {report['failed']} FAILED ⚠️")
    else:
        print(" ✅")
    print()

    # 表格输出
    print(f"  {'Model':<8} {'Dataset':<10} {'Train Acc':>10} {'Test Acc':>10} Status")
    print("  " + "-" * 50)
    for r in report["results"]:
        train = f"{r.get('train_accuracy', 0):.2%}"
        test = f"{r.get('test_accuracy', 0):.2%}"
        status = "✅" if r["status"] == "passed" else f"❌ {r.get('error', 'error')[:20]}"
        print(f"  {r['model']:<8} {r['dataset']:<10} {train:>10} {test:>10} {status}")

    print("═" * 60)
    print()
    print("💡 解读 Benchmark 报告:")
    print("  • Test Accuracy < Train Accuracy 明显 → 可能过拟合")
    print("  • KNN 在 circles 上表现差 → 数据分布不规则，考虑 SVM/RBF")
    print("  • Tree depth 大会过拟合 → 建议跑 python main.py --model Tree --dataset circles --depth 1~10")
    print("  • 完整回归检测: python3 -m benchmarks")
    print()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Quick benchmark harness")
    parser.add_argument("--quick", action="store_true", help="Quick smoke test (default)")
    args = parser.parse_args()

    print("🚀 开始 Quick Benchmark（2 datasets × 4 models）...")
    report = run_quick_benchmark()
    print_summary(report)

    # 保存到 reports/
    os.makedirs("benchmarks/reports", exist_ok=True)
    date_str = datetime.now().strftime("%Y-%m-%d")
    json_path = f"benchmarks/reports/{date_str}_quick.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"💾 JSON 报告已保存: {json_path}")
    print(f"   用 ml-db benchmark inspect 查看详情")
