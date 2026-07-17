#!/usr/bin/env python3
"""
ML Decision Boundary Visualizer
Real-time visualization of how different ML models partition feature space
"""

# Re-exported from core for backward compatibility with tests/ and benchmarks/
# The canonical implementations live in core/datasets.py and core/train_utils.py

from core.datasets import (
    make_circles,
    make_moons,
    make_blobs,
    make_xor,
    make_s_curve,
    DATASET_GENERATORS,
)
from core.train_utils import (
    build_model,
    slider_to_params,
    compute_boundary_grid,
    get_model_info_dict,
)
from core.validation import (
    validate_dataset,
    validate_model_params,
    DatasetValidationError,
)
from core.error_messages import E1007_UNKNOWN_DATASET, E3005_INVALID_PARAM_FORMAT, format_error
from core.registry import get_registry_manager

# Import sklearn directly for main.py-only helpers (visualization, experiment orchestration)
from sklearn.datasets import make_circles as sk_circles, make_moons as sk_moons, make_blobs as sk_blobs, make_s_curve as sk_s_curve
from sklearn.preprocessing import KBinsDiscretizer

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from pathlib import Path
import argparse

# Model implementations
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier, ExtraTreesClassifier, AdaBoostClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB


# ── CLI Interface ───────────────────────────────────────────────────────────────


def parse_args():
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        prog="ml-decision-boundary",
        description="ML Decision Boundary Visualizer — visualize how ML models partition feature space.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py                          # Run all experiments + visualizations
  python main.py --model SVM --dataset circles  # Run single experiment
  python main.py --list-models            # List available models and datasets
        """,
    )
    parser.add_argument(
        "--model", "-m",
        choices=["SVM", "LR", "Tree", "RF", "KNN", "MLP", "NB", "GB", "ET", "AB"],
        help="Model type to run (default: all)",
    )
    parser.add_argument(
        "--dataset", "-d",
        choices=["circles", "moons", "blobs", "xor", "s_curve"],
        help="Dataset to use (default: all)",
    )
    parser.add_argument(
        "--n-samples", "-n", type=int, default=500,
        help="Number of samples per dataset (default: 500)",
    )
    parser.add_argument(
        "--noise", type=float, default=0.3,
        help="Noise level for synthetic data (default: 0.3)",
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Random seed for reproducibility (default: 42)",
    )
    parser.add_argument(
        "--output", "-o", default="output",
        help="Output directory for results and plots (default: output/)",
    )
    parser.add_argument(
        "--list-models", action="store_true",
        help="List available models and datasets, then exit",
    )
    parser.add_argument(
        "--params", "-p", nargs="+", action="append",
        help="Model-specific parameters as KEY=VALUE pairs, e.g. --params C=10 kernel=rbf",
    )
    parser.add_argument(
        "--resolution", "-r", type=int, default=200,
        help="Decision boundary grid resolution (default: 200)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable verbose output",
    )
    parser.add_argument(
        "--no-registry", action="store_true",
        help="Disable model registry (default: registry enabled)",
    )

    # v8 DoD #3: model subcommand group
    subparsers = parser.add_subparsers(dest="model_cmd", help="Model registry management")

    # ml-db model list
    list_parser = subparsers.add_parser("model", help="Model registry management")
    list_parser.add_argument("action", choices=["list", "inspect", "delete", "compare", "tag", "untag", "tags"],
                              help="Action: list, inspect, delete, compare, tag, untag, tags")
    list_parser.add_argument("model_id", nargs="?", help="Model ID (required for inspect/delete/compare/tag/untag)")
    list_parser.add_argument("model_id2", nargs="?", help="Second model ID (for compare)")
    list_parser.add_argument("--tag", dest="tag_name", help="Tag name (for tag/untag/list --tag)")
    list_parser.add_argument("--remove-tag", dest="remove_tag", help="Remove tag name (for untag)")

    # v8 DoD #4: benchmark subcommand group
    bench_parser = subparsers.add_parser("benchmark", help="Benchmark registry management")
    bench_parser.add_argument("action", choices=["list", "inspect", "regressions"],
                              help="Action: list, inspect <id>, or regressions [current_id]")
    bench_parser.add_argument("benchmark_id", nargs="?", help="Benchmark ID (optional for inspect/regressions)")

    return parser.parse_args()


def list_models():
    """Print available models and datasets."""
    models = {
        "SVM": "Support Vector Machine (RBF/linear/poly kernels)",
        "LR": "Logistic Regression",
        "Tree": "Decision Tree",
        "RF": "Random Forest",
        "KNN": "K-Nearest Neighbors",
        "MLP": "Multi-Layer Perceptron",
        "NB": "Gaussian Naive Bayes",
        "GB": "Gradient Boosting Classifier",
        "ET": "Extra Trees Classifier",
        "AB": "AdaBoost Classifier",
    }
    datasets = {
        "circles": "Interleaved circles (sklearn.make_circles)",
        "moons": "Semicircle moons (sklearn.make_moons)",
        "blobs": "Gaussian blobs (sklearn.make_blobs, 3 centers)",
        "xor": "XOR-style nonlinear pattern",
        "s_curve": "S-curve manifold (sklearn.make_s_curve, 3D projected to 2D)",
    }
    print("Available models:")
    for name, desc in models.items():
        print(f"  {name:6s} — {desc}")
    print("\nAvailable datasets:")
    for name, desc in datasets.items():
        print(f"  {name:8s} — {desc}")


# ── v8 DoD #3: Model Registry CLI ─────────────────────────────────────────────


def cmd_model_list(rm):
    """List all registered models."""
    models = rm.list_models()
    if not models:
        print("📭 No models registered yet. Run an experiment to register your first model.")
        return
    # Print table header
    print(f"\n{'ID':<22} {'TYPE':<8} {'ACCURACY':<10} {'CREATED':<25}")
    print("-" * 70)
    for m in models:
        created = m.get("created_at", "unknown")[:25]
        acc = m.get("accuracy", m.get("metrics", {}).get("test_accuracy", 0.0))
        print(f"{m['id']:<22} {m['model_type']:<8} {acc:<10.4f} {created}")
    print(f"\n✅ {len(models)} model(s) registered")


def cmd_model_inspect(rm, model_id):
    """Show detailed metadata for a specific model."""
    try:
        meta = rm.get_metadata(model_id)
    except FileNotFoundError:
        print(f"❌ Model '{model_id}' not found. Run 'python main.py model list' to see available models.")
        raise SystemExit(1)
    print(f"\n🔍 Model: {meta['id']}")
    print(f"   Type:         {meta['model_type']}")
    print(f"   Plugin:       {meta.get('plugin_origin', False)}")
    print(f"   Accuracy:     {meta.get('accuracy', 'N/A')}")
    print(f"   Created:      {meta.get('created_at', 'unknown')}")
    print(f"   Hyperparameters: {meta.get('hyperparameters', {})}")
    print(f"   Dataset:      {meta.get('dataset', {})}")
    print(f"   Metrics:      {meta.get('metrics', {})}")
    tags = meta.get('tags', [])
    print(f"   Tags:         {tags if tags else '(none)'}")
    if meta.get('plugin_state'):
        print(f"   Plugin State: {meta['plugin_state']}")
    print(f"   Joblib:       {meta.get('joblib_path', 'N/A')}")


def cmd_model_delete(rm, model_id):
    """Delete a registered model."""
    try:
        rm.get_metadata(model_id)  # Verify it exists first
    except FileNotFoundError:
        print(f"❌ Model '{model_id}' not found. Run 'python main.py model list' to see available models.")
        raise SystemExit(1)
    rm.delete_model(model_id)
    print(f"🗑️  Deleted model: {model_id}")


def cmd_model_compare(rm, model_id1: str, model_id2: str):
    """Compare accuracy and metadata of two registered models.  v9 DoD #3."""
    try:
        result = rm.compare_models(model_id1, model_id2)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        raise SystemExit(1)

    m1, m2 = result["model1"], result["model2"]
    print(f"\n⚖️  Model Comparison")
    print(f"   model1: {m1['id']} ({m1['model_type']}, acc={m1.get('accuracy', 'N/A')})")
    print(f"   model2: {m2['id']} ({m2['model_type']}, acc={m2.get('accuracy', 'N/A')})")
    print()
    print(f"{'FIELD':<30} {'MODEL1':<15} {'MODEL2':<15} NOTE")
    print("-" * 80)
    for d in result["differences"]:
        f = d["field"]
        v1 = str(d["value1"])[:15]
        v2 = str(d["value2"])[:15]
        note = d.get("note", "")
        print(f"{f:<30} {v1:<15} {v2:<15} {note}")
    print()
    # Highlight accuracy winner
    acc_diff = next((d for d in result["differences"] if d["field"] == "test_accuracy"), None)
    if acc_diff:
        winner = acc_diff["winner"]
        if winner == "model1":
            print(f"🏆 Winner: {m1['id']} (model1) — {acc_diff['note']}")
        elif winner == "model2":
            print(f"🏆 Winner: {m2['id']} (model2) — {acc_diff['note']}")
        else:
            print("🤝 Result: Tie — identical test accuracy")


def cmd_model_tag(rm, model_id: str, tag: str):
    """Add a tag to a model.  v9 DoD #3."""
    try:
        rm.tag_model(model_id, tag)
    except FileNotFoundError:
        print(f"❌ Model '{model_id}' not found. Run 'python main.py model list' to see available models.")
        raise SystemExit(1)
    except ValueError as e:
        print(f"❌ {e}")
        raise SystemExit(1)
    print(f"🏷️  Tagged model {model_id} with '{tag}'")


def cmd_model_untag(rm, model_id: str, tag: str):
    """Remove a tag from a model.  v9 DoD #3."""
    try:
        rm.untag_model(model_id, tag)
    except FileNotFoundError:
        print(f"❌ Model '{model_id}' not found. Run 'python main.py model list' to see available models.")
        raise SystemExit(1)
    except ValueError as e:
        print(f"❌ {e}")
        raise SystemExit(1)
    print(f"🏷️  Removed tag '{tag}' from model {model_id}")


def cmd_model_tags(rm):
    """List all tags and the models that have them.  v9 DoD #3."""
    tag_index = rm.list_tags()
    if not tag_index:
        print("📭 No tags found. Use 'python main.py model tag <id> --tag <name>' to add tags.")
        return
    print(f"\n🏷️  All Tags ({len(tag_index)} total):")
    print()
    for tag, model_ids in sorted(tag_index.items()):
        print(f"  【{tag}】 — {len(model_ids)} model(s)")
        for mid in model_ids:
            try:
                meta = rm.get_metadata(mid)
                acc = meta.get("accuracy", "N/A")
                mtype = meta.get("model_type", "?")
                print(f"     {mid:<22} {mtype:<8} acc={acc}")
            except Exception:
                print(f"     {mid}")
        print()


# ── v8 DoD #4: Benchmark Registry CLI ─────────────────────────────────────────


def cmd_benchmark_list(rm):
    """List all registered benchmark runs."""
    benchmarks = rm.list_benchmarks()
    if not benchmarks:
        print("📭 No benchmark runs registered yet. Run a benchmark to register your first result.")
        return
    print(f"\n{'ID':<30} {'MODE':<12} {'DATE':<25} {'DUR':<8} {'PASS':<6} {'FAIL':<6} {'REGR':<6}")
    print("-" * 100)
    for b in benchmarks:
        bid = b.get('id', 'unknown')[:30]
        mode = b.get('mode', 'unknown')[:12]
        date = b.get('timestamp', 'unknown')[:25]
        dur = f"{b.get('duration_seconds', 0):.1f}s"
        passed = b.get('passed', 0)
        failed = b.get('failed', 0)
        regr = b.get('regressions', 0)
        print(f"{bid:<30} {mode:<12} {date:<25} {dur:<8} {passed:<6} {failed:<6} {regr:<6}")
    print(f"\n✅ {len(benchmarks)} benchmark run(s) registered")


def cmd_benchmark_inspect(rm, benchmark_id):
    """Show detailed metadata for a specific benchmark run."""
    try:
        meta = rm.get_benchmark(benchmark_id)
    except FileNotFoundError:
        print(f"❌ Benchmark '{benchmark_id}' not found. Run 'python main.py benchmark list' to see available runs.")
        raise SystemExit(1)
    print(f"\n🔍 Benchmark: {meta['id']}")
    print(f"   Mode:          {meta.get('mode', 'N/A')}")
    print(f"   Timestamp:    {meta.get('timestamp', 'N/A')}")
    print(f"   Duration:     {meta.get('duration_seconds', 'N/A')}s")
    print(f"   Git Hash:     {meta.get('git_hash', 'N/A')}")
    print(f"   Total:        {meta.get('total_experiments', 'N/A')}")
    print(f"   Passed:       {meta.get('passed', 'N/A')}")
    print(f"   Failed:       {meta.get('failed', 'N/A')}")
    print(f"   Regressions:  {meta.get('regressions', 'N/A')}")
    if meta.get('regression_details'):
        print(f"\n   📉 Regression Details:")
        for rd in meta['regression_details']:
            print(f"      - {rd.get('dataset')}/{rd.get('model')}: "
                  f"{rd.get('previous_accuracy')} → {rd.get('current_accuracy')} "
                  f"(-{rd.get('drop_pct')}%, -{rd.get('drop')})")
    if meta.get('model_results'):
        print(f"\n   📊 Model Results ({len(meta['model_results'])} total):")
        for mr in meta['model_results'][:5]:
            print(f"      - {mr.get('dataset')}/{mr.get('model')}: acc={mr.get('accuracy', 'N/A')}")
        if len(meta['model_results']) > 5:
            print(f"      ... and {len(meta['model_results']) - 5} more")
    if meta.get('report_md'):
        print(f"\n   📄 Report: {meta.get('report_md', 'N/A')}")


def cmd_benchmark_regressions(rm, current_run_id):
    """Detect regressions vs previous run (or vs specified run)."""
    result = rm.detect_regressions(current_run_id=current_run_id)
    if result.get("error"):
        print(f"⚠️  {result['error']}")
        return
    if not result.get("has_regressions"):
        print(f"✅ No regressions detected ({result.get('count', 0)} checks)")
        return
    print(f"\n🚨 Regression Alert: {result.get('count')} regression(s) detected!")
    for detail in result.get("details", []):
        print(f"   📉 {detail['dataset']}/{detail['model']}: "
              f"{detail['previous_accuracy']} → {detail['current_accuracy']} "
              f"(-{detail['drop_pct']}%, -{detail['drop']})")


def parse_params(params_list: list) -> dict:
    """Parse KEY=VALUE parameter list into a dict."""
    result = {}
    if not params_list:
        return result
    for item in params_list:
        for pair in item:
            if "=" not in pair:
                raise ValueError(format_error(E3005_INVALID_PARAM_FORMAT, pair=pair))
            key, val = pair.split("=", 1)
            # Try to convert to int/float/bool, else keep as string
            for typ in (int, float):
                try:
                    result[key] = typ(val)
                    break
                except ValueError:
                    pass
            else:
                # Keep as string, handle bool
                if val.lower() in ("true", "false"):
                    result[key] = val.lower() == "true"
                else:
                    result[key] = val
    return result


@dataclass
class ModelResult:
    """Single model experiment result"""
    name: str
    params: dict
    accuracy: float
    train_time: float
    boundary_points: List[List[float]]  # Contour line coordinates
    support_vectors: Optional[int] = None
    tree_depth: Optional[int] = None
    n_layers: Optional[int] = None
    n_trees: Optional[int] = None
    max_depth: Optional[int] = None
    n_estimators: Optional[int] = None


def generate_dataset(dataset_name: str, n_samples: int = 500, noise: float = 0.3, seed: int = 42) -> Tuple:
    """Generate synthetic classification datasets.

    Delegates to the canonical implementations in core/datasets.py.
    Validates output before returning.
    """
    if dataset_name not in DATASET_GENERATORS:
        raise ValueError(format_error(E1007_UNKNOWN_DATASET, name=dataset_name))
    X, y = DATASET_GENERATORS[dataset_name](n_samples, noise, seed)
    # Boundary validation — raises DatasetValidationError with actionable message
    validate_dataset(X, y, dataset_name=dataset_name)
    return X, y


def train_model(model_type: str, params: dict, X_train, y_train) -> Tuple:
    """Train a model and return (trained_model, train_time)"""
    import time

    models = {
        "SVM": lambda: SVC(**params, random_state=42),
        "LR": lambda: LogisticRegression(**params, random_state=42, max_iter=1000),
        "Tree": lambda: DecisionTreeClassifier(**params, random_state=42),
        "RF": lambda: RandomForestClassifier(**params, random_state=42),
        "KNN": lambda: KNeighborsClassifier(**params),
        "MLP": lambda: MLPClassifier(**params, random_state=42, max_iter=2000),
        "NB": lambda: GaussianNB(**params),
        "GB": lambda: GradientBoostingClassifier(**params, random_state=42),
        "ET": lambda: ExtraTreesClassifier(**params, random_state=42),
        "AB": lambda: AdaBoostClassifier(**params, random_state=42, algorithm='SAMME'),
    }

    if model_type not in models:
        # Provide helpful error with available options (including plugins)
        try:
            from core.plugins.registry import discover_plugins
            plugins = discover_plugins()
            builtin_list = list(models.keys())
            plugin_list = list(plugins.keys())
            all_options = builtin_list + plugin_list
        except Exception:
            all_options = list(models.keys())
        raise ValueError(
            f"Unknown model: '{model_type}'. "
            f"Available models: {', '.join(all_options)}. "
            f"Run with --list-models to see all."
        )

    model = models[model_type]()
    start = time.perf_counter()
    model.fit(X_train, y_train)
    train_time = time.perf_counter() - start

    return model, train_time


def get_model_info(model, model_type: str) -> dict:
    """Extract model-specific info"""
    info = {}
    if model_type == "SVM":
        info["support_vectors"] = len(model.support_vectors_)
    elif model_type == "Tree":
        info["tree_depth"] = model.get_depth()
    elif model_type == "RF":
        info["n_trees"] = len(model.estimators_)
        info["max_depth"] = max(e.get_depth() for e in model.estimators_)
    elif model_type == "MLP":
        info["n_layers"] = len(model.hidden_layer_sizes)
    elif model_type == "GB":
        info["n_estimators"] = model.n_estimators
        info["max_depth"] = model.max_depth
    elif model_type == "ET":
        info["n_estimators"] = len(model.estimators_)
        info["max_depth"] = max(e.get_depth() for e in model.estimators_)
    elif model_type == "AB":
        info["n_estimators"] = model.n_estimators
    return info


def compute_decision_boundary(model, X_train, resolution=200) -> Tuple:
    """Compute decision boundary mesh"""
    x_min, x_max = X_train[:, 0].min() - 0.5, X_train[:, 0].max() + 0.5
    y_min, y_max = X_train[:, 1].min() - 0.5, X_train[:, 1].max() + 0.5

    xx, yy = np.meshgrid(
        np.linspace(x_min, x_max, resolution),
        np.linspace(y_min, y_max, resolution)
    )

    Z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)

    return xx, yy, Z


def plot_decision_boundary(ax, model, X_train, y_train, xx, yy, Z, title: str):
    """Plot decision boundary on axis"""
    # Color maps
    cmap_light = ListedColormap(['#FFAAAA', '#AAAAFF', '#AAFFAA'])
    cmap_bold = ['#FF4444', '#4444FF', '#44FF44']

    # Plot regions
    ax.contourf(xx, yy, Z, alpha=0.4, cmap=cmap_light)

    # Plot decision boundary line
    ax.contour(xx, yy, Z, colors='black', linewidths=0.5, alpha=0.5)

    # Plot training points
    classes = np.unique(y_train)
    markers = ['o', 's', '^']
    for i, c in enumerate(classes):
        ax.scatter(
            X_train[y_train == c, 0], X_train[y_train == c, 1],
            c=cmap_bold[i % len(cmap_bold)], marker=markers[i % len(markers)],
            s=30, edgecolors='white', linewidth=0.5, alpha=0.8
        )

    ax.set_title(title, fontsize=11, fontweight='bold')
    ax.set_xlabel('Feature 1')
    ax.set_ylabel('Feature 2')


def run_experiment(dataset: str, model_type: str, params: dict, seed: int = 42, use_registry: bool = True, verbose: bool = False) -> ModelResult:
    """Run single experiment"""
    # Validate model params before training
    validate_model_params(model_type, params)
    X, y = generate_dataset(dataset, n_samples=500, noise=0.3, seed=seed)

    # Split data (simple holdout)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )

    # Train model
    model, train_time = train_model(model_type, params, X_train, y_train)


    # Evaluate
    train_accuracy = model.score(X_train, y_train)
    test_accuracy = model.score(X_test, y_test)


    # Compute boundary
    xx, yy, Z = compute_decision_boundary(model, X_train)

    # Extract model info
    info = get_model_info(model, model_type)

    # Auto-register model to registry
    if use_registry:
        try:
            rm = get_registry_manager()
            model_id = rm.save_model(
                model=model,
                model_type=model_type,
                hyperparameters=params,
                X_train=X_train,
                y_train=y_train,
                dataset_name=dataset,
                n_samples=X_train.shape[0],
                train_accuracy=train_accuracy,
                test_accuracy=test_accuracy,
                plugin_origin=False,
            )
            if verbose:
                print(f"  📦 Registered model: {model_id}")
        except Exception as e:
            if verbose:
                print(f"  ⚠️  Registry error (non-fatal): {e}")


    return ModelResult(
        name=f"{model_type}_{dataset}",
        params=params,
        accuracy=test_accuracy,
        train_time=train_time,
        boundary_points=[],  # Store for advanced analysis
        **info
    )


def run_all_experiments(use_registry: bool = True, verbose: bool = False):
    """Run comprehensive experiments"""
    datasets = ["circles", "moons", "blobs", "xor", "s_curve"]
    models = {
        "SVM": [
            {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
            {"kernel": "rbf", "C": 10.0, "gamma": "scale"},
            {"kernel": "linear", "C": 1.0},
        ],
        "LR": [
            {"C": 1.0},
            {"C": 10.0},
            {"C": 0.1},
        ],
        "Tree": [
            {"max_depth": 3},
            {"max_depth": 10},
            {"max_depth": None},
        ],
        "RF": [
            {"n_estimators": 50, "max_depth": 5},
            {"n_estimators": 100, "max_depth": 10},
            {"n_estimators": 200, "max_depth": None},
        ],
        "KNN": [
            {"n_neighbors": 3},
            {"n_neighbors": 7},
            {"n_neighbors": 15},
        ],
        "MLP": [
            {"hidden_layer_sizes": (50,), "alpha": 0.001},
            {"hidden_layer_sizes": (100, 50), "alpha": 0.001},
            {"hidden_layer_sizes": (50, 50, 50), "alpha": 0.01},
        ],
        "GB": [
            {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
            {"n_estimators": 200, "max_depth": 5, "learning_rate": 0.05},
        ],
        "ET": [
            {"n_estimators": 100, "max_depth": 10},
            {"n_estimators": 200, "max_depth": 15},
        ],
        "AB": [
            {"n_estimators": 50, "learning_rate": 1.0},
            {"n_estimators": 100, "learning_rate": 1.0},
        ],
    }

    results = []
    for dataset in datasets:
        print(f"\n📊 Dataset: {dataset}")
        for model_type, param_list in models.items():
            for params in param_list:
                try:
                    result = run_experiment(dataset, model_type, params, use_registry=use_registry, verbose=verbose)
                    results.append(result)
                    print(f"  ✅ {model_type} C={params.get('C', params.get('max_depth', 'N/A'))}: acc={result.accuracy:.4f} time={result.train_time:.4f}s")
                except Exception as e:
                    print(f"  ❌ {model_type} {params}: {e}")

    return results


def generate_comparison_plots(results: List[ModelResult], output_dir: str = "output"):
    """Generate comparison visualization plots"""
    os.makedirs(output_dir, exist_ok=True)

    datasets = ["circles", "moons", "blobs", "xor"]
    model_types = ["SVM", "LR", "Tree", "RF", "KNN", "MLP"]

    # Plot 1: Model comparison heatmap
    fig, ax = plt.subplots(figsize=(14, 8))

    accuracy_matrix = []
    for dataset in datasets:
        row = []
        for model_type in model_types:
            matching = [r for r in results if model_type in r.name and dataset in r.name]
            if matching:
                row.append(max(matching, key=lambda x: x.accuracy).accuracy)
            else:
                row.append(0)
        accuracy_matrix.append(row)

    im = ax.imshow(accuracy_matrix, cmap='RdYlGn', aspect='auto', vmin=0.5, vmax=1.0)

    ax.set_xticks(range(len(model_types)))
    ax.set_xticklabels(model_types, fontsize=12)
    ax.set_yticks(range(len(datasets)))
    ax.set_yticklabels(datasets, fontsize=12)

    # Add text annotations
    for i in range(len(datasets)):
        for j in range(len(model_types)):
            text = ax.text(j, i, f"{accuracy_matrix[i][j]:.2f}",
                          ha="center", va="center", color="black", fontsize=11)

    ax.set_title("Model Accuracy Comparison Heatmap", fontsize=14, fontweight='bold')
    plt.colorbar(im, ax=ax, label='Accuracy')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/accuracy_heatmap.png", dpi=150)
    plt.close()
    print(f"📈 Saved: {output_dir}/accuracy_heatmap.png")

    # Plot 2: Training time comparison
    fig, ax = plt.subplots(figsize=(12, 6))

    time_data = {}
    for model_type in model_types:
        times = [r.train_time for r in results if model_type in r.name]
        time_data[model_type] = times

    bp = ax.boxplot([time_data[m] for m in model_types], labels=model_types, patch_artist=True)
    colors = plt.cm.Set3(np.linspace(0, 1, len(model_types)))
    for patch, color in zip(bp['boxes'], colors):
        patch.set_facecolor(color)

    ax.set_ylabel('Training Time (seconds)')
    ax.set_title('Training Time Distribution by Model Type', fontsize=14, fontweight='bold')
    ax.set_yscale('log')
    plt.tight_layout()
    plt.savefig(f"{output_dir}/training_time_boxplot.png", dpi=150)
    plt.close()
    print(f"📈 Saved: {output_dir}/training_time_boxplot.png")

    # Plot 3: Decision boundaries for best model per dataset
    fig, axes = plt.subplots(2, 4, figsize=(20, 10))
    axes = axes.flatten()

    for idx, dataset in enumerate(datasets):
        X, y = generate_dataset(dataset, n_samples=500, noise=0.3)

        # Find best model for this dataset
        dataset_results = [r for r in results if dataset in r.name]
        best = max(dataset_results, key=lambda x: x.accuracy)

        # Retrain best model
        model, _ = train_model(
            best.name.split('_')[0],
            best.params,
            X, y
        )

        # Plot
        ax = axes[idx]
        xx, yy, Z = compute_decision_boundary(model, X)

        cmap_light = ListedColormap(['#FFAAAA', '#AAAAFF'])
        ax.contourf(xx, yy, Z, alpha=0.4, cmap=cmap_light)
        ax.contour(xx, yy, Z, colors='black', linewidths=0.5, alpha=0.5)
        for c in [0, 1]:
            ax.scatter(X[y == c, 0], X[y == c, 1], s=20, alpha=0.6)
        ax.set_title(f"{dataset}\nBest: {best.name} ({best.accuracy:.3f})", fontsize=11)
        ax.set_xlabel('Feature 1')
        ax.set_ylabel('Feature 2')

        # Show all models for this dataset
        ax = axes[idx + 4]
        ax.axis('off')
        model_text = "\n".join([
            f"{r.name.split('_')[0]} ({r.params}): {r.accuracy:.3f}"
            for r in sorted(dataset_results, key=lambda x: -x.accuracy)[:6]
        ])
        ax.text(0.1, 0.5, f"Models on {dataset}:\n{model_text}", fontsize=9,
               transform=ax.transAxes, verticalalignment='center',
               family='monospace')

    plt.tight_layout()
    plt.savefig(f"{output_dir}/best_models_grid.png", dpi=150)
    plt.close()
    print(f"📈 Saved: {output_dir}/best_models_grid.png")


def generate_single_model_visualization(model_type: str, dataset: str, output_dir: str = "output"):
    """Generate detailed visualization for single model on single dataset"""
    os.makedirs(output_dir, exist_ok=True)

    X, y = generate_dataset(dataset, n_samples=500, noise=0.3)

    # Train all variants of this model type
    model_configs = {
        "SVM": [
            {"kernel": "rbf", "C": 0.1, "gamma": "scale"},
            {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
            {"kernel": "rbf", "C": 10.0, "gamma": "scale"},
            {"kernel": "linear", "C": 1.0},
        ],
        "Tree": [
            {"max_depth": 1},
            {"max_depth": 3},
            {"max_depth": 7},
            {"max_depth": 15},
        ],
        "KNN": [
            {"n_neighbors": 1},
            {"n_neighbors": 5},
            {"n_neighbors": 15},
            {"n_neighbors": 50},
        ],
    }

    if model_type not in model_configs:
        print(f"No configs for {model_type}")
        return

    configs = model_configs[model_type]
    n_configs = len(configs)

    fig, axes = plt.subplots(1, n_configs, figsize=(4 * n_configs, 4))
    if n_configs == 1:
        axes = [axes]

    results = []
    for ax, params in zip(axes, configs):
        model, train_time = train_model(model_type, params, X, y)
        accuracy = model.score(X, y)

        xx, yy, Z = compute_decision_boundary(model, X)

        cmap_light = ListedColormap(['#FFAAAA', '#AAAAFF'])
        ax.contourf(xx, yy, Z, alpha=0.4, cmap=cmap_light)
        ax.contour(xx, yy, Z, colors='black', linewidths=0.5, alpha=0.5)
        for c in [0, 1]:
            ax.scatter(X[y == c, 0], X[y == c, 1], s=15, alpha=0.6)

        param_str = ", ".join([f"{k}={v}" for k, v in params.items()])
        ax.set_title(f"{param_str}\nAcc: {accuracy:.3f}, Time: {train_time:.4f}s", fontsize=9)
        ax.set_xlabel('Feature 1')
        ax.set_ylabel('Feature 2')

        results.append({
            "params": params,
            "accuracy": accuracy,
            "train_time": train_time
        })

        # Extract model-specific info
        if model_type == "SVM":
            results[-1]["n_support_vectors"] = len(model.support_vectors_)
        elif model_type == "Tree":
            results[-1]["tree_depth"] = model.get_depth()

    plt.suptitle(f"{model_type} on {dataset} - Parameter Effect", fontsize=14, fontweight='bold')
    plt.tight_layout()

    filename = f"{output_dir}/{model_type}_{dataset}_params.png"
    plt.savefig(filename, dpi=150, bbox_inches='tight')
    plt.close()
    print(f"📈 Saved: {filename}")

    return results


def save_results(results: List[ModelResult], output_path: str):
    """Save experiment results as JSON"""
    data = {
        "experiments": [],
        "summary": {
            "total_experiments": len(results),
            "best_accuracy": max(r.accuracy for r in results) if results else float('nan'),
            "fastest_train_time": min(r.train_time for r in results) if results else float('nan'),
            "model_types": list(set(r.name.split('_')[0] for r in results)) if results else [],
            "datasets": list(set(r.name.split('_')[1] for r in results)) if results else [],
        }
    }

    for r in results:
        exp = {
            "name": r.name,
            "accuracy": r.accuracy,
            "train_time": r.train_time,
            "params": r.params,
        }
        # Add optional fields
        if hasattr(r, 'support_vectors') and r.support_vectors is not None:
            exp["support_vectors"] = r.support_vectors
        if hasattr(r, 'tree_depth') and r.tree_depth is not None:
            exp["tree_depth"] = r.tree_depth
        if hasattr(r, 'n_layers') and r.n_layers is not None:
            exp["n_layers"] = r.n_layers
        data["experiments"].append(exp)

    with open(output_path, 'w') as f:
        json.dump(data, f, indent=2)
    print(f"💾 Saved results: {output_path}")


if __name__ == "__main__":
    args = parse_args()

    if args.list_models:
        list_models()
        raise SystemExit(0)

    # v8 DoD #3/#4: model and benchmark registry subcommands (routed by args.model_cmd value)
    if args.model_cmd:
        rm = get_registry_manager()
        cmd = args.model_cmd  # "model" or "benchmark"
        action = args.action  # shared across both subparsers

        if cmd == "model":
            if action == "list":
                # v9 DoD #3: support --tag filter
                if args.tag_name:
                    models = rm.list_models_by_tag(args.tag_name)
                    if not models:
                        print(f"📭 No models found with tag '{args.tag_name}'.")
                    else:
                        print(f"\n🏷️  Models tagged '{args.tag_name}' ({len(models)}):")
                        for m in models:
                            created = m.get("created_at", "unknown")[:25]
                            acc = m.get("accuracy", 0.0)
                            print(f"   {m['id']:<22} {m['model_type']:<8} acc={acc:.4f}  {created}")
                else:
                    cmd_model_list(rm)
            elif action == "inspect":
                if not args.model_id:
                    print("❌ inspect requires a model_id: python main.py model inspect <id>")
                    raise SystemExit(1)
                cmd_model_inspect(rm, args.model_id)
            elif action == "delete":
                if not args.model_id:
                    print("❌ delete requires a model_id: python main.py model delete <id>")
                    raise SystemExit(1)
                cmd_model_delete(rm, args.model_id)
            elif action == "compare":
                if not args.model_id or not args.model_id2:
                    print("❌ compare requires two model IDs: python main.py model compare <id1> <id2>")
                    raise SystemExit(1)
                cmd_model_compare(rm, args.model_id, args.model_id2)
            elif action == "tag":
                if not args.model_id or not args.tag_name:
                    print("❌ tag requires model_id and --tag <name>: python main.py model tag <id> --tag <name>")
                    raise SystemExit(1)
                cmd_model_tag(rm, args.model_id, args.tag_name)
            elif action == "untag":
                if not args.model_id:
                    print("❌ untag requires model_id: python main.py model untag <id> --tag <name> or --remove-tag <name>")
                    raise SystemExit(1)
                tag_name = args.tag_name or args.remove_tag
                if not tag_name:
                    print("❌ untag requires --tag <name> or --remove-tag <name>")
                    raise SystemExit(1)
                cmd_model_untag(rm, args.model_id, tag_name)
            elif action == "tags":
                cmd_model_tags(rm)
        elif cmd == "benchmark":
            if action == "list":
                cmd_benchmark_list(rm)
            elif action == "inspect":
                if not args.benchmark_id:
                    print("❌ inspect requires a benchmark_id: python main.py benchmark inspect <id>")
                    raise SystemExit(1)
                cmd_benchmark_inspect(rm, args.benchmark_id)
            elif action == "regressions":
                cmd_benchmark_regressions(rm, args.benchmark_id)
        raise SystemExit(0)

    if args.verbose:
        print("=" * 60)
        print("🎯 ML Decision Boundary Visualizer")
        print("=" * 60)

    # If no specific model/dataset, run all
    run_all = not (args.model or args.dataset)

    if run_all:
        if args.verbose:
            print("\n📊 Running all experiments...")
        results = run_all_experiments(use_registry=not args.no_registry, verbose=args.verbose)
        if args.verbose:
            print(f"   Completed {len(results)} experiments.")

        if args.verbose:
            print("\n📈 Generating comparison plots...")
        generate_comparison_plots(results, output_dir=args.output)

        if args.verbose:
            print("\n🔍 Generating parameter effect plots...")
        for model_type in ["SVM", "Tree", "KNN"]:
            for dataset in ["circles", "moons", "xor"]:
                generate_single_model_visualization(model_type, dataset, output_dir=args.output)

        if args.verbose:
            print("\n💾 Saving results...")
        save_results(results, f"{args.output}/experiment_results.json")

        if args.verbose:
            print("\n" + "=" * 60)
            print("✅ All experiments complete!")
            print(f"📁 Check '{args.output}/' directory for visualizations")
            print("=" * 60)
    else:
        # Run single or filtered experiment
        model = args.model or "SVM"
        dataset = args.dataset or "circles"
        params = parse_params(args.params) if args.params else {}

        if args.verbose:
            print(f"\n▶️  Running single experiment: model={model}, dataset={dataset}, params={params}")

        result = run_experiment(dataset, model, params, seed=args.seed, use_registry=not args.no_registry, verbose=args.verbose)

        # Plot and save
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(8, 6))
        X, y = generate_dataset(dataset, args.n_samples, args.noise, args.seed)
        trained_model, _ = train_model(model, params, X, y)
        xx, yy, Z = compute_decision_boundary(trained_model, X)
        plot_decision_boundary(ax, trained_model, X, y, xx, yy, Z,
                               title=f"{model} on {dataset}")
        os.makedirs(args.output, exist_ok=True)
        out_path = f"{args.output}/{model}_{dataset}.png"
        fig.savefig(out_path, dpi=150, bbox_inches="tight")
        plt.close()

        if args.verbose:
            print(f"\n✅ Saved: {out_path}")
            print(f"   Accuracy: {result.accuracy:.4f}")
            print(f"   Train time: {result.train_time:.4f}s")