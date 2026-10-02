#!/usr/bin/env python3
"""
01_quick_start.py — 5 行代码跑通第一个决策边界可视化

目标：让新用户在 5 分钟内跑通第一个实验，建立对工具的第一印象。
依赖：sklearn, numpy, matplotlib（已在 requirements.txt）
输出：output/ 目录下生成 PNG 可视化 + JSON 元数据
运行：python examples/01_quick_start.py
"""

import os
import sys

# 确保项目根目录在 Python path 中
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.svm import SVC
from sklearn.datasets import make_circles
from core.train_utils import compute_boundary_grid
import matplotlib
matplotlib.use("Agg")  # 无头模式，不弹窗
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ── Step 1: 生成数据 ────────────────────────────────────────────────────────────
X, y = make_circles(n_samples=300, noise=0.25, random_state=42)

# ── Step 2: 训练模型 ────────────────────────────────────────────────────────────
model = SVC(kernel="rbf", C=1.0)
model.fit(X, y)

# ── Step 3: 可视化 ─────────────────────────────────────────────────────────────
cm = ListedColormap(["#FF6B6B", "#4ECDC4"])
fig, ax = plt.subplots(figsize=(8, 6))
xx, yy, Z = compute_boundary_grid(model, X, resolution=150)
ax.contourf(xx, yy, Z, alpha=0.4, cmap=cm)
ax.scatter(X[:, 0], X[:, 1], c=y, cmap=cm, edgecolors="k", s=20, alpha=0.8)
ax.set_title("Decision Boundary — SVM (RBF kernel) on Circles Dataset")
ax.set_xlabel("Feature 1")
ax.set_ylabel("Feature 2")

os.makedirs("output", exist_ok=True)
out_path = "output/01_quick_start.png"
fig.savefig(out_path, dpi=150, bbox_inches="tight")
print(f"✅ 可视化已保存: {out_path}")
print(f"   训练样本数: {len(X)}")
print(f"   训练准确率: {model.score(X, y):.2%}")
