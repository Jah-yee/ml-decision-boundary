# ml-decision-boundary Cookbook

> **版本**: v1.0（v9 DoD #2 — 2026-07-07）
> **前置条件**: `pip install -r requirements.txt`
> **测试**: Python 3.8+

实用指南，解决问题：`C8 — 文档示例不足，新用户上手困难`。

---

## 目录

1. [快速上手](#1-快速上手)
2. [模型选择指南](#2-模型选择指南)
3. [使用 Model Registry](#3-使用-model-registry)
4. [编写自定义插件](#4-编写自定义插件)
5. [解读 Benchmark 报告](#5-解读-benchmark-报告)
6. [FAQ / 故障排查](#6-faq--故障排查)

---

## 1. 快速上手

### 1.1 安装

```bash
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt
```

### 1.2 运行第一个实验

```bash
python3 main.py
```

输出示例（circles 数据集）：

```
📊 Dataset: circles
  ✅ SVM C=1.0:       acc=0.9200  time=0.084s
  ✅ RandomForest depth=10: acc=0.9600  time=0.231s
  ✅ KNN k=15:        acc=0.9100  time=0.011s
```

产物：
- `output/*.png` — 决策边界可视化
- `output/*.json` — 结构化结果

### 1.3 单模型 + 指定数据集

```bash
python3 main.py --model SVM --dataset xor
```

### 1.4 查看可用模型和数据

```bash
python3 main.py --list-models
```

### 1.5 理解输出文件

| 文件 | 内容 |
|------|------|
| `boundary_<model>_<dataset>.png` | 决策边界热力图 + 散点 |
| `results_<dataset>.json` | 结构化精度和超参数 |

### 1.6 常见错误

| 症状 | 原因 | 解决 |
|------|------|------|
| `E1007 Unknown dataset` | 数据集名拼错 | 用 `--list-models` 查看可用 |
| `E2001 Unknown model` | 模型名拼错 | 用 `--list-models` 查看可用 |
| `ModuleNotFoundError` | 未安装依赖 | `pip install -r requirements.txt` |
| `Hyperparameter range empty` | 超参数范围为空 | 检查 `--param-range` 参数 |

---

## 2. 模型选择指南

### 2.1 什么时候用什么模型

| 数据集特征 | 推荐模型 | 原因 |
|-----------|---------|------|
| 线性可分 | LR, SVM (linear) | 简单、可解释、训练快 |
| 非线性边界 | SVM (RBF), MLP | 捕捉复杂决策面 |
| 交互式 / 实时 | Tree, RF | 推理快，边界易可视化 |
| 高维稀疏 | LR, SVM | 正则化效果好 |
| 需要概率输出 | LR, MLP | 可输出 `predict_proba` |
| 不确定数据 | GB, AB | 集成方法更鲁棒 |

### 2.2 超参数对决策边界的影响

#### SVM

| 参数 | 值越大 → | 值越小 → |
|------|---------|---------|
| `C`（正则化强度） | 更复杂边界（过拟合风险↑） | 更平滑边界（欠拟合风险↑） |
| `gamma`（RBF 核） | 复杂局部边界 | 平滑全局边界 |

```bash
# 高正则化（简单边界）
python3 main.py --model SVM --params C=0.01 --dataset circles

# 低正则化（复杂边界）
python3 main.py --model SVM --params C=100 --dataset circles
```

#### Decision Tree

| 参数 | 值越大 → | 值越小 → |
|------|---------|---------|
| `max_depth` | 越深→越复杂边界 | 越浅→越平滑边界 |
| `min_samples_leaf` | 叶节点越多→越复杂 | 叶节点少→更泛化 |

```bash
# 深度限制
python3 main.py --model Tree --params max_depth=3 --dataset xor
python3 main.py --model Tree --params max_depth=15 --dataset xor
```

#### KNN

| 参数 | 值越大 → | 值越小 → |
|------|---------|---------|
| `k`（邻居数） | 越平滑边界 | 越复杂边界（噪音敏感↑） |

```bash
python3 main.py --model KNN --params k=3 --dataset moons
python3 main.py --model KNN --params k=50 --dataset moons
```

#### MLP

| 参数 | 影响 |
|------|------|
| `hidden_layer_sizes` | 隐藏层宽度/深度 |
| `alpha`（L2 正则化） | 类似 SVM C，越大越平滑 |

```bash
python3 main.py --model MLP --params hidden_layer_sizes=50 --dataset xor
```

### 2.3 针对不同数据集的推荐模型

| 数据集 | 难度 | 最佳模型 | 备注 |
|--------|------|---------|------|
| `circles` | ⭐ 简单 | SVM RBF, RF | 嵌套圆结构 |
| `moons` | ⭐⭐ 中等 | SVM RBF, KNN | 半月形，需非线性 |
| `blobs` | ⭐ 简单 | LR, SVM, Tree | 线性可分（3类） |
| `xor` | ⭐⭐⭐ 困难 | Tree (deep), MLP | 非线性，无通用解 |
| `s_curve` | ⭐⭐⭐ 困难 | RF, SVM RBF | 3D 投影到 2D |

### 2.4 模型对比实验

```bash
# 对比 4 个模型在同一数据集上的表现
python3 examples/02_model_comparison.py --dataset circles
```

---

## 3. 使用 Model Registry

> v8 引入。训练结果自动持久化到 `~/.ml-decision-boundary/registry/`。

### 3.1 Registry 目录结构

```
~/.ml-decision-boundary/registry/
├── models/
│   ├── 2026-07-07_abc123.json   # 元数据
│   └── 2026-07-07_abc123.joblib # 序列化模型
└── benchmarks/
    └── 2026-07-07_xyz789.json   # benchmark 结果
```

### 3.2 CLI 命令

```bash
# 列出所有已注册模型
python3 main.py model list

# 查看模型详情
python3 main.py model inspect 2026-07-07_abc123

# 删除模型
python3 main.py model delete 2026-07-07_abc123

# 列出所有 benchmark
python3 main.py benchmark list

# 查看 benchmark 详情
python3 main.py benchmark inspect 2026-07-07_xyz789

# 检测精度回归
python3 main.py benchmark regressions
```

### 3.3 Python API

```python
from core.registry import get_registry_manager

rm = get_registry_manager()

# 列出所有模型
models = rm.list_models()
for m in models:
    print(f"{m['id']}: {m['model_type']} acc={m['accuracy']}")

# 查看单个模型
meta = rm.get_metadata("2026-07-07_abc123")
print(meta)

# 删除模型
rm.delete_model("2026-07-07_abc123")
```

### 3.4 模型元数据结构

```json
{
  "id": "2026-07-07_abc123",
  "model_type": "SVM",
  "hyperparameters": {"C": 1.0, "kernel": "rbf"},
  "dataset": {
    "name": "circles",
    "n_samples": 500,
    "hash": "sha256:..."
  },
  "metrics": {
    "train_accuracy": 0.94,
    "test_accuracy": 0.92
  },
  "accuracy": 0.92,
  "created_at": "2026-07-07T09:30:00.000000+00:00",
  "plugin_origin": false,
  "joblib_path": "models/2026-07-07_abc123.joblib"
}
```

### 3.5 追踪实验迭代

每次运行 `main.py`（默认模式）会自动注册模型。通过 `model list` 查看历史，找到最高精度模型：

```bash
python3 main.py model list | sort -k3 -r | head
```

### 3.6 模型加载与使用

```python
from core.registry import get_registry_manager

rm = get_registry_manager()
model = rm.load_model("2026-07-07_abc123")

# model 是一个 sklearn 估计器，可直接使用
import numpy as np
X_new = np.array([[0.5, 0.5]])
pred = model.predict(X_new)
print(pred)
```

---

## 4. 编写自定义插件

### 4.1 插件接口

在 `core/plugins/models/` 下创建文件，继承 `ModelBuilder`：

```python
# core/plugins/models/my_model.py

from core.interfaces import ModelBuilder
from sklearn.base import BaseEstimator, ClassifierMixin
from typing import Any, Dict, List


class MyCustomModel(BaseEstimator, ClassifierMixin, ModelBuilder):
    """
    自定义分类器示例。
    继承 ModelBuilder 以获得插件能力。
    """

    @property
    def name(self) -> str:
        return "MYMODEL"

    @property
    def description(self) -> str:
        return "My Custom Model — brief description"

    def build(self, **kwargs) -> Any:
        # 使用 kwargs 中的超参数构建 sklearn 估计器
        param = kwargs.get("my_param", 1.0)
        return _MyEstimator(param=param)

    def default_params(self) -> Dict[str, Any]:
        return {"my_param": 1.0}

    def hyperparameter_space(self) -> Dict[str, List[Any]]:
        return {
            "my_param": [0.1, 0.5, 1.0, 5.0, 10.0],
        }


class _MyEstimator(BaseEstimator, ClassifierMixin):
    """实际的 sklearn 估计器实现。"""

    def __init__(self, param: float = 1.0):
        self.param = param

    def fit(self, X, y):
        # TODO: 实现训练逻辑
        self.classes_ = sorted(set(y))
        return self

    def predict(self, X):
        # TODO: 实现预测逻辑
        import numpy as np
        return np.zeros(len(X), dtype=int)

    def predict_proba(self, X):
        # 可选：实现概率输出
        import numpy as np
        return np.ones((len(X), len(self.classes_))) / len(self.classes_)
```

### 4.2 注册插件

**方式 A：CLI flag**

```bash
python3 main.py --model MYMODEL --dataset circles
```

**方式 B：代码中设置**

在 `core/plugins/__init__.py` 或 `main.py` 中导入插件：

```python
from core.plugins.models import my_model  # 导入即注册
```

### 4.3 序列化支持（v8 DoD #2）

如果插件有内部状态需要持久化，实现 `get_state` / `from_state`：

```python
def get_state(self) -> Dict[str, Any]:
    return {
        "plugin_name": self.name,
        "hyperparameters": self.default_params(),
        # 其他需要持久化的状态
    }

@classmethod
def from_state(cls, state: Dict[str, Any]) -> "MyCustomModel":
    instance = cls()
    return instance
```

### 4.4 调试插件

```python
from core.plugins.models.my_model import MyCustomModel

builder = MyCustomModel()
model = builder.build(my_param=2.0)
print(model)  # 确认构建成功

# 测试序列化
state = builder.get_state()
restored = MyCustomModel.from_state(state)
print(restored)
```

---

## 5. 解读 Benchmark 报告

### 5.1 运行 Benchmark

```bash
# 完整 suite（慢）
python3 -m benchmarks

# 快速验证
python3 examples/05_benchmark_harness.py --quick
```

### 5.2 Benchmark 报告结构

```json
{
  "id": "2026-07-07_xyz789",
  "mode": "quick",
  "timestamp": "2026-07-07T09:30:00+00:00",
  "duration_seconds": 42.5,
  "git_hash": "abc1234",
  "total_experiments": 50,
  "passed": 49,
  "failed": 1,
  "regressions": 1,
  "model_results": [
    {
      "model": "SVM",
      "dataset": "circles",
      "accuracy": 0.92,
      "train_time": 0.08
    }
  ],
  "regression_details": [
    {
      "model": "KNN",
      "dataset": "moons",
      "current_accuracy": 0.78,
      "previous_accuracy": 0.85,
      "drop": 0.07,
      "drop_pct": 8.24
    }
  ]
}
```

### 5.3 Regression Detection 逻辑

- **触发条件**：`(previous_accuracy - current_accuracy) / previous_accuracy > 5%`
- 默认阈值：`REGRESSION_THRESHOLD = 0.05`（5%）
- 阈值可调：`RegistryManager().detect_regressions(threshold=0.10)`

```python
from core.registry import get_registry_manager

rm = get_registry_manager()
result = rm.detect_regressions(threshold=0.05)

if result["has_regressions"]:
    print(f"发现 {result['count']} 个回归：")
    for detail in result["details"]:
        print(f"  {detail['model']} on {detail['dataset']}: "
              f"{detail['previous_accuracy']} → {detail['current_accuracy']} "
              f"(-{detail['drop_pct']}%)")
```

### 5.4 解读模型精度

| 精度范围 | 含义 |
|---------|------|
| `≥ 0.95` | 优秀，模型和数据匹配良好 |
| `0.80 – 0.95` | 良好，大多数场景可接受 |
| `0.60 – 0.80` | 一般，可能需要调参或换模型 |
| `< 0.60` | 差，数据集或模型选择有问题 |

### 5.5 Benchmark 与 Registry 的关系

- **Registry**：记录每次训练的元数据（单模型）
- **Benchmark**：记录完整实验套件的结果（含回归检测）
- Benchmark 报告自动保存到 `~/.ml-decision-boundary/registry/benchmarks/`

---

## 6. FAQ / 故障排查

### 6.1 安装问题

**Q: `ModuleNotFoundError: No module named 'sklearn'`**

```bash
pip install -r requirements.txt
```

**Q: `matplotlib` 相关警告**

警告可忽略（不影响功能）。如需消除：

```bash
pip install matplotlib --upgrade
```

### 6.2 运行问题

**Q: `python3 main.py` 无输出**

检查是否在正确目录：

```bash
cd ml-decision-boundary
python3 main.py
```

**Q: `E1007 Unknown dataset: 'circle'`（单数形式）**

正确名称是 `circles`（复数）。用 `--list-models` 查看准确名称。

**Q: `E2001 Unknown model: 'svm'`**

正确名称是 `SVM`（大写）。完整列表：

```
SVM, LR, Tree, RF, KNN, MLP, NB, GB, ET, AB
```

### 6.3 pytest 超时问题（C4 技术债）

**Q: `pytest -q` 在 C4 阶段挂起不退出**

这是已知问题（C4），已在 `tests/test_main_coverage.py` 中 patch 目标修正：

```python
# ✅ 正确（patch 测试模块命名空间）
@patch("tests.test_main_coverage.run_all_experiments")

# ❌ 错误（patch main 模块，无法拦截本地引用）
@patch("main.run_all_experiments")
```

如遇超时，手动运行：

```bash
timeout 120 python3 -m pytest tests/test_main_coverage.py -q
```

### 6.4 序列化兼容性

**Q: 加载旧版本 joblib 文件报错**

Joblib 文件与 sklearn 版本绑定。升级 sklearn 后重新训练：

```bash
python3 main.py --model SVM --dataset circles
# 重新生成 joblib 文件
```

### 6.5 Git push 问题

**Q: `remote: error: GH007: Your push would publish a private email address.`**

GitHub 账户的 email 设置为私有。解决方法：

1. 访问 https://github.com/settings/emails
2. 取消勾选 "Keep my email address private"
3. 或勾选 "Allow publishing emails"

然后重新 push：

```bash
git push origin feat/v8-model-registry-core
```

### 6.6 Registry 文件位置

**Q: Registry 保存在哪里？**

默认：`~/.ml-decision-boundary/registry/`

可通过环境变量覆盖：

```python
import os
os.environ["ML_DECISION_BOUNDARY_REGISTRY"] = "/custom/path"
from core.registry import get_registry_manager
rm = get_registry_manager()  # 使用自定义路径
```

### 6.7 模型精度波动

**Q: 同一命令跑两次精度不一样**

使用固定 seed 获得确定性结果：

```bash
python3 main.py --seed 42 --model SVM --dataset circles
```

默认每次运行使用不同随机 seed，导致精度略有波动。

### 6.8 如何贡献插件

1. 在 `core/plugins/models/` 下创建新文件
2. 继承 `ModelBuilder` 接口
3. 实现 `name`、`build`、`default_params`
4. 可选实现 `get_state`/`from_state` 用于序列化
5. 在 `core/plugins/__init__.py` 中添加导入
6. 提交 PR，标题：`feat(plugin): add <ModelName> model plugin`

---

## 附录：错误码参考

| 错误码 | 含义 |
|-------|------|
| `E1001` | 数据集为空 |
| `E1002` | 数据集样本数不足（需 ≥ 2） |
| `E1003` | X 和 y 长度不匹配 |
| `E1004` | 只有 1 个类别 |
| `E1005` | 数据全是 NaN/Inf |
| `E1007` | 未知数据集名称 |
| `E2001` | 未知模型名称 |
| `E2002` | 模型初始化失败 |
| `E3001` | 超参数值无效（如 C ≤ 0） |
