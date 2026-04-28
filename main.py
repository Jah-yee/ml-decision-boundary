#!/usr/bin/env python3
"""
ML Decision Boundary Visualizer
Real-time visualization of how different ML models partition feature space
"""

import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap
import json
import os
from dataclasses import dataclass, asdict
from typing import List, Tuple, Optional
from pathlib import Path

# Model implementations
from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB


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


def generate_dataset(dataset_name: str, n_samples: int = 500, noise: float = 0.3, seed: int = 42) -> Tuple:
    """Generate synthetic classification datasets"""
    np.random.seed(seed)
    
    datasets = {
        "circles": lambda: make_circles(n_samples, noise, seed),
        "moons": lambda: make_moons(n_samples, noise, seed),
        "blobs": lambda: make_blobs(n_samples, seed),
        "xor": lambda: make_xor(n_samples, noise, seed),
    }
    
    if dataset_name not in datasets:
        raise ValueError(f"Unknown dataset: {dataset_name}")
    
    return datasets[dataset_name]()


def make_circles(n, noise, seed):
    from sklearn.datasets import make_circles as sk_circles
    X, y = sk_circles(n_samples=n, noise=noise, random_state=seed, factor=0.5)
    return X, y


def make_moons(n, noise, seed):
    from sklearn.datasets import make_moons as sk_moons
    X, y = sk_moons(n_samples=n, noise=noise, random_state=seed)
    return X, y


def make_blobs(n, seed):
    from sklearn.datasets import make_blobs
    X, y = make_blobs(n_samples=n, centers=3, random_state=seed, cluster_std=1.5)
    return X, y


def make_xor(n, noise, seed):
    np.random.seed(seed)
    X = np.random.randn(n, 2)
    y = ((X[:, 0] > 0) ^ (X[:, 1] > 0)).astype(int)
    # Add noise
    X += np.random.randn(n, 2) * noise
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
    }
    
    if model_type not in models:
        raise ValueError(f"Unknown model: {model_type}")
    
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


def run_experiment(dataset: str, model_type: str, params: dict, seed: int = 42) -> ModelResult:
    """Run single experiment"""
    X, y = generate_dataset(dataset, n_samples=500, noise=0.3, seed=seed)
    
    # Split data (simple holdout)
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=seed
    )
    
    # Train model
    model, train_time = train_model(model_type, params, X_train, y_train)
    
    # Evaluate
    accuracy = model.score(X_test, y_test)
    
    # Compute boundary
    xx, yy, Z = compute_decision_boundary(model, X_train)
    
    # Extract model info
    info = get_model_info(model, model_type)
    
    return ModelResult(
        name=f"{model_type}_{dataset}",
        params=params,
        accuracy=accuracy,
        train_time=train_time,
        boundary_points=[],  # Store for advanced analysis
        **info
    )


def run_all_experiments():
    """Run comprehensive experiments"""
    datasets = ["circles", "moons", "blobs", "xor"]
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
    }
    
    results = []
    for dataset in datasets:
        print(f"\n📊 Dataset: {dataset}")
        for model_type, param_list in models.items():
            for params in param_list:
                try:
                    result = run_experiment(dataset, model_type, params)
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
    print("=" * 60)
    print("🎯 ML Decision Boundary Visualizer")
    print("=" * 60)
    
    # Run all experiments
    print("\n📊 Running experiments...")
    results = run_all_experiments()
    
    # Generate visualizations
    print("\n📈 Generating plots...")
    generate_comparison_plots(results)
    
    # Generate detailed param effect plots
    print("\n🔍 Generating parameter effect plots...")
    for model_type in ["SVM", "Tree", "KNN"]:
        for dataset in ["circles", "moons", "xor"]:
            generate_single_model_visualization(model_type, dataset)
    
    # Save results
    print("\n💾 Saving results...")
    save_results(results, "output/experiment_results.json")
    
    print("\n" + "=" * 60)
    print("✅ All experiments complete!")
    print("📁 Check 'output/' directory for visualizations")
    print("=" * 60)