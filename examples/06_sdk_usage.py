#!/usr/bin/env python3
"""
examples/06_sdk_usage.py — v12 DoD #1: Python SDK walkthrough

Demonstrates the `ml_db` SDK:
  1. instantiate MLDB
  2. list available datasets / models
  3. train + register a model
  4. predict with the registered model
  5. tag, compare and list models

Run:
    python examples/06_sdk_usage.py
"""

import sys
from pathlib import Path

# Allow running from a source checkout without installation
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ml_db import MLDB  # noqa: E402


def main() -> int:
    db = MLDB()

    print("=" * 60)
    print("ml_db SDK — v12 DoD #1")
    print("=" * 60)

    print(f"\nDatasets: {', '.join(db.datasets())}")
    print(f"Models:   {', '.join(db.models())}")

    # ── Train ────────────────────────────────────────────────────────────────
    print("\n--- Training (SVM on circles) ---")
    result = db.train(
        model="SVM",
        dataset="circles",
        n_samples=500,
        noise=0.3,
        tags=["sdk-demo"],
    )
    print(f"model_id       : {result.model_id}")
    print(f"accuracy       : {result.accuracy:.4f}")
    print(f"train_accuracy : {result.train_accuracy:.4f}")
    print(f"train_time     : {result.train_time:.4f}s")

    # ── Predict ──────────────────────────────────────────────────────────────
    print("\n--- Predicting ---")
    points = [[0.0, 0.0], [1.0, 1.0], [-1.0, -1.0]]
    preds = db.predict(result.model_id, X=points)
    for point, pred in zip(points, preds):
        print(f"  {point} -> {pred}")

    batch = db.predict_batch(result.model_id, X=points)
    print(f"batch count: {batch['count']}")

    # ── Registry ─────────────────────────────────────────────────────────────
    print("\n--- Registry ---")
    print(f"registered models : {len(db.list_models())}")
    print(f"tags              : {db.list_tags()}")
    tagged = db.list_models_by_tag("sdk-demo")
    print(f"models tagged 'sdk-demo': {[m['id'] for m in tagged]}")

    # ── Compare two models ───────────────────────────────────────────────────
    other = db.train(model="Tree", dataset="circles", n_samples=500, tags=["sdk-demo"])
    comparison = db.compare(result.model_id, other.model_id)
    print("\n--- Comparison (SVM vs Tree) ---")
    for diff in comparison["differences"]:
        print(f"  {diff['field']}: {diff['value1']} vs {diff['value2']} → {diff['winner']}")

    print("\n✅ SDK demo complete")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
