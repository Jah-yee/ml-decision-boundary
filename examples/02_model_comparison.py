#!/usr/bin/env python3
"""
02_model_comparison.py — 同一数据集上对比 4 种模型的决策边界

目标：展示不同模型（SVM/Tree/KNN/MLP）对同一数据的几何理解差异。
依赖：sklearn, numpy, matplotlib（已在 requirements.txt）
输出：output/02_model_comparison.png — 2x2 子图对比
运行：python examples/02_model_comparison.py
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.svm import SVC
from sklearn.tree import DecisionTreeClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.datasets import make_moons
from core.train_utils import compute_boundary_grid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ── 数据 ──────────────────────────────────────────────────────────────────────
X, y = make_moons(n_samples=300, noise=0.2, random_state=42)

# ── 模型列表 ────────────────────────────────────────────────────────────────────
MODELS = [
    ("SVM (RBF)", SVC(kernel="rbf", C=1.0)),
    ("Decision Tree (depth=5)", DecisionTreeClassifier(max_depth=5, random_state=42)),
    ("KNN (k=7)", KNeighborsClassifier(n_neighbors=7)),
    ("MLP (100,50)", MLPClassifier(hidden_layer_sizes=(100, 50), max_iter=1000, random_state=42)),
]

cm = ListedColormap(["#FF6B6B", "#4ECDC4"])

fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes = axes.flatten()

for ax, (name, model) in zip(axes, MODELS):
    model.fit(X, y)
    xx, yy, Z = compute_boundary_grid(model, X, resolution=100)
    ax.contourf(xx, yy, Z, alpha=0.4, cmap=cm)
    ax.scatter(X[:, 0], X[:, 1], c=y, cmap=cm, edgecolors="k", s=15, alpha=0.7)
    acc = model.score(X, y)
    ax.set_title(f"{name}\nAccuracy: {acc:.2%}")
    ax.set_xlabel("Feature 1")
    ax.set_ylabel("Feature 2")

fig.suptitle("Model Comparison — Moons Dataset", fontsize=14, fontweight="bold")
plt.tight_layout()

os.makedirs("output", exist_ok=True)
out_path = "output/02_model_comparison.png"
fig.savefig(out_path, dpi=150, bbox_inches="tight")

print(f"✅ 模型对比图已保存: {out_path}")
for name, model in MODELS:
    acc = model.score(X, y)
    print(f"   {name:30s} — 准确率: {acc:.2%}")
