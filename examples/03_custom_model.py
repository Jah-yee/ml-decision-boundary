#!/usr/bin/env python3
"""
03_custom_model.py — 使用自定义插件模型

目标：展示如何编写并使用自定义 ModelBuilder 插件。
依赖：sklearn, numpy, matplotlib（已在 requirements.txt）
输出：output/03_custom_model.png
运行：python examples/03_custom_model.py

本例创建了一个 GradientBoostingClassifier 插件（不依赖外部文件，
直接演示接口），并在同一数据集上与内置 SVM 对比。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.datasets import make_circles
from sklearn.ensemble import GradientBoostingClassifier
from core.interfaces import ModelBuilder
from core.plugins.registry import discover_plugins, get_plugin_model
from core.train_utils import compute_boundary_grid
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

# ── Step 1: 定义自定义插件（演示接口）────────────────────────────────────────────
# 实际项目中将此类放入 core/plugins/models/my_model.py

class GradientBoostingPlugin(ModelBuilder):
    """Gradient Boosting — 自定义插件示例。"""

    name = "GradientBoosting"
    description = "Gradient Boosting Classifier (plugin)"

    def build(self, **kwargs):
        return GradientBoostingClassifier(
            n_estimators=kwargs.get("n_estimators", 100),
            max_depth=kwargs.get("max_depth", 3),
            learning_rate=kwargs.get("learning_rate", 0.1),
            random_state=42,
        )

    def default_params(self):
        return {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1}

    def hyperparameter_space(self):
        return {
            "n_estimators": [50, 100, 200],
            "max_depth": [2, 3, 5],
            "learning_rate": [0.05, 0.1, 0.2],
        }


# ── Step 2: 使用插件（两种方式）────────────────────────────────────────────────

# 方式A：直接实例化
plugin_model = GradientBoostingPlugin()
print(f"插件名称: {plugin_model.name}")
print(f"默认参数: {plugin_model.default_params()}")

# 方式B：从插件注册表发现（需要文件存在于 core/plugins/models/）
plugins = discover_plugins()
print(f"已发现插件: {list(plugins.keys())}")

# ── Step 3: 训练 + 可视化 ───────────────────────────────────────────────────────

X, y = make_circles(n_samples=300, noise=0.25, random_state=42)

model = plugin_model.build(**plugin_model.default_params())
model.fit(X, y)

cm = ListedColormap(["#FF6B6B", "#4ECDC4"])
fig, ax = plt.subplots(figsize=(8, 6))
xx, yy, Z = compute_boundary_grid(model, X, resolution=120)
ax.contourf(xx, yy, Z, alpha=0.4, cmap=cm)
ax.scatter(X[:, 0], X[:, 1], c=y, cmap=cm, edgecolors="k", s=20, alpha=0.8)
ax.set_title("Decision Boundary — GradientBoosting (Custom Plugin)\non Circles Dataset")
ax.set_xlabel("Feature 1")
ax.set_ylabel("Feature 2")

os.makedirs("output", exist_ok=True)
out_path = "output/03_custom_model.png"
fig.savefig(out_path, dpi=150, bbox_inches="tight")

print(f"\n✅ 自定义插件可视化已保存: {out_path}")
print(f"   训练准确率: {model.score(X, y):.2%}")
print("\n要创建真实插件：")
print("  1. 在 core/plugins/models/ 下创建 your_model.py")
print("  2. 继承 ModelBuilder，实现 build() / get_state() / from_state()")
print("  3. 重启 Python — discover_plugins() 会自动发现")
