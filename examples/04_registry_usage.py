#!/usr/bin/env python3
"""
04_registry_usage.py — 使用 Model Registry 管理实验

目标：展示如何将训练结果注册到 Registry、如何查看和加载历史模型。
依赖：core.registry（已在项目中）
输出：打印到终端（无文件产出）
运行：python examples/04_registry_usage.py

Registry 目录：~/.ml-decision-boundary/registry/models/
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sklearn.svm import SVC
from sklearn.datasets import make_circles, make_moons
from sklearn.model_selection import train_test_split
from core.registry import get_registry_manager

# ── Step 1: 初始化 Registry ────────────────────────────────────────────────────

rm = get_registry_manager()
print(f"Registry 目录: {rm.registry_base}")
print()

# ── Step 2: 列出已有模型 ───────────────────────────────────────────────────────

models = rm.list_models()
print(f"📦 已注册模型数量: {len(models)}")
if models:
    print(f"   最新模型: {models[0]['id']} ({models[0]['model_type']})")
print()

# ── Step 3: 训练并注册新模型 ────────────────────────────────────────────────────

print("🔧 训练新模型...")
X, y = make_circles(n_samples=500, noise=0.2, random_state=42)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = SVC(kernel="rbf", C=1.0, gamma="scale")
model.fit(X_train, y_train)

train_acc = model.score(X_train, y_train)
test_acc = model.score(X_test, y_test)
print(f"   训练准确率: {train_acc:.2%}")
print(f"   测试准确率: {test_acc:.2%}")

# 注册到 Registry
model_id = rm.save_model(
    model=model,
    model_type="SVM",
    hyperparameters={"kernel": "rbf", "C": 1.0, "gamma": "scale"},
    X_train=X_train,
    y_train=y_train,
    dataset_name="circles",
    n_samples=len(X),
    train_accuracy=train_acc,
    test_accuracy=test_acc,
)
print(f"\n✅ 模型已注册: {model_id}")
print()

# ── Step 4: 查看元数据 ─────────────────────────────────────────────────────────

metadata = rm.get_metadata(model_id)
print(f"📋 元数据:")
print(f"   模型ID: {metadata['id']}")
print(f"   类型: {metadata['model_type']}")
print(f"   数据集: {metadata['dataset']['name']} ({metadata['dataset']['n_samples']} samples)")
print(f"   精度: {metadata['accuracy']:.2%}")
print(f"   创建时间: {metadata['created_at']}")
print()

# ── Step 5: 加载已注册的模型 ──────────────────────────────────────────────────

loaded_model = rm.load_model(model_id)
loaded_acc = loaded_model.score(X_test, y_test)
print(f"📥 重新加载模型验证: {loaded_acc:.2%}（与测试精度一致={loaded_acc == test_acc:.0f}）")
print()

# ── Step 6: 按标签列出（示例，无标签时为空）────────────────────────────────────

print("🏷️  所有已注册模型:")
all_models = rm.list_models()
for m in all_models[:5]:  # 只显示最新5个
    tags = m.get("tags", [])
    tag_str = f" [{', '.join(tags)}]" if tags else ""
    print(f"   {m['id']} — {m['model_type']} — acc={m['accuracy']:.2%}{tag_str}")

if len(all_models) > 5:
    print(f"   ... 还有 {len(all_models) - 5} 个")

print()
print("💡 Registry CLI 命令:")
print("   ml-db model list              # 列出所有注册模型")
print("   ml-db model inspect <id>      # 查看模型详情")
print("   ml-db model delete <id>       # 删除模型")
