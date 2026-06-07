# ADR-0013 — v8 DoD 细化：Model Registry & Lifecycle

**日期**: 2026-06-07
**状态**: Proposed
**维护人**: 太子

---

## 背景

ADR-0012 已确定 v8 主题为 **Model Registry & Lifecycle**，并列出候选方向。本 ADR 将其细化为可验证的 DoD 项目。

---

## v8 DoD 细化

| # | DoD 项目 | 验收标准 | 优先级 | 备注 |
|---|---------|---------|--------|------|
| 1 | **Model Registry 核心** | 训练结果自动注册到 `~/.ml-decision-boundary/registry/`；每次训练生成唯一 ID，元数据 JSON 含模型类型、超参数、数据集 hash、训练时间、精度 | P1 | 对应 ADR-0012 方向 #1 |
| 2 | **模型序列化** | `save_model()` / `load_model()` 接口，支持插件模型和内置模型；序列化文件存于 registry | P1 | 对应 ADR-0012 方向 #2 |
| 3 | **CLI 模型管理** | `ml-db model list` / `ml-db model inspect <id>` / `ml-db model delete <id>` 三个子命令 | P1 | 对应 ADR-0012 方向 #3 |
| 4 | **ADR-0013 Accepted 后同步** | 将本 DoD 同步至 NEXT_ROUND_THEME.md | P0 | 元任务 |

---

## DoD #1 详细设计：Model Registry 核心

### 目标
每次训练自动将结果持久化到 `~/.ml-decision-boundary/registry/`，支持实验追溯和模型复用。

### Registry 目录结构

```
~/.ml-decision-boundary/registry/
├── models/
│   ├── 2026-06-07_abc123.json   # 元数据
│   ├── 2026-06-07_def456.json
│   └── ...
└── benchmarks/
    ├── 2026-06-07_xyz789.json
    └── ...
```

### 元数据 Schema（`models/*.json`）

```json
{
  "id": "2026-06-07_abc123",
  "model_type": "SVM",
  "hyperparameters": {"C": 1.0, "kernel": "rbf"},
  "dataset": {
    "name": "moons",
    "n_samples": 200,
    "hash": "sha256:..."
  },
  "metrics": {
    "train_accuracy": 0.97,
    "test_accuracy": 0.94
  },
  "created_at": "2026-06-07T09:57:00+08:00",
  "plugin_origin": false
}
```

### 验收标准
1. 首次运行 `python3 main.py` 后 registry 目录自动创建
2. 每次运行后 `~/.ml-decision-boundary/registry/models/` 下有对应 JSON 文件
3. JSON 文件可被 `load_model()` 读取并还原模型
4. `--no-registry` flag 可禁用注册（默认开启）

### 实现位置
- `core/registry.py`（新增，RegistryManager 类）
- `main.py`（集成注册调用）
- `tests/test_registry.py`（新增）

---

## DoD #2 详细设计：模型序列化

### 目标
支持 `save_model()` / `load_model()` 接口，序列化模型到 registry 目录。

### 接口设计（提案）

```python
# core/registry.py
import json, joblib, hashlib
from pathlib import Path

REGISTRY_BASE = Path.home() / ".ml-decision-boundary" / "registry"

class RegistryManager:
    def save_model(self, model, model_type, hyperparameters, dataset_info, metrics):
        """持久化模型到 registry/"""
        # 生成唯一 ID（日期 + 短 hash）
        # 保存元数据 JSON
        # 使用 joblib 序列化模型对象

    def load_model(self, model_id):
        """从 registry 加载模型"""
        # 读取元数据 + 反序列化模型对象

    def list_models(self):
        """返回所有注册模型元数据列表"""
```

### 验收标准
1. `RegistryManager.save_model()` 生成 `.joblib` 文件 + `.json` 元数据
2. `RegistryManager.load_model(<id>)` 可完整还原模型
3. 内置模型（SVM、Tree、KNN、MLP）全部可序列化
4. 插件模型通过相同接口序列化（插件需实现 `get_state()` 方法）

### 风险
- sklearn 模型 pickle/joblib 兼容性（需验证）
- 插件模型序列化协议需在接口文档中明确

---

## DoD #3 详细设计：CLI 模型管理

### 目标
提供 `ml-db model` 子命令集合，方便用户查看和管理已注册的模型。

### CLI 设计

```bash
# 列出所有注册模型
ml-db model list

# 查看指定模型详情
ml-db model inspect <id>

# 删除指定模型
ml-db model delete <id>

# 加载并使用已注册模型（下次训练时引用）
ml-db model use <id>
```

### 验收标准

| 命令 | 输出示例 |
|------|---------|
| `ml-db model list` | 表格展示 ID、类型、精度、创建时间 |
| `ml-db model inspect <id>` | 完整元数据 + 数据集 hash + 超参数 |
| `ml-db model delete <id>` | 确认后删除，更新列表 |
| 未知 ID | 友好错误：`Model '<id>' not found. Run 'ml-db model list' to see available models.` |

### 实现位置
- `core/cli.py`（扩展 `model` 子命令）
- `core/registry.py`（`list_models`, `load_model`, `delete_model` 方法）

---

## 版本历史

- v1 (2026-06-07): Initial — v8 DoD 细化，基于 ADR-0012 方向展开