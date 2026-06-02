# ADR-0011 — v7 DoD 细化：Extensibility, Edge Cases & UX

**日期**: 2026-06-01
**状态**: Accepted (PR#50 merged, DoD #1 complete)
**维护人**: 太子

---

## 背景

ADR-0010 已确定 v7 主题为 **Extensibility, Edge Cases & UX**，并列出候选方向。本 ADR 将其细化为可验证的 DoD 项目。

---

## v7 DoD 细化

| # | DoD 项目 | 验收标准 | 优先级 | 备注 |
|---|---------|---------|--------|------|
| 1 | **自定义模型插件接口** ✅ | 用户在 `core/plugins/models/` 目录下放置 Python 文件即可注册新模型，无需修改核心代码；至少一个内置模型可通过插件机制加载 | P1 | PR#50 merged |
| 2 | **数据集边界验证** | 输入空数据集、单类数据集、极端值时，CLI/API 返回可操作的错误信息（非 traceback） | P1 | 对应 ADR-0010 方向 #2 |
| 3 | **错误信息改进** | 所有 CLI/API 错误给出人类可读的「行动建议」而非 Python traceback | P1 | 对应 ADR-0010 方向 #3 |
| 4 | **C4: pytest 超时修复** | 解决 sklearn MLP 收敛导致 pytest 超时的问题（非阻塞，但需要诊断） | P3 | 对应 ADR-0010 方向 #6 |
| 5 | **ADR-0011 Accepted 后更新 NEXT_ROUND_THEME** | 将本 DoD 同步至 NEXT_ROUND_THEME.md | P0 | 元任务，确保信息一致 |

---

## DoD #1 详细设计：自定义模型插件接口

### 目标
贡献者只需在 `core/plugins/models/` 目录下添加一个 Python 文件（实现模型构建逻辑），无需修改 `core/` 核心代码，即可扩展支持的模型类型。

### 验收标准
1. `core/plugins/models/` 目录存在（若不存在则自动创建）
2. 目录中每个 `.py` 文件（不含 `__init__.py` 和以 `_` 开头的文件）自动注册
3. 注册后 `python3 main.py --model <name>` 可使用该模型
4. 内置模型 `SVM` 可通过插件机制重新加载（验证接口兼容性）
5. 插件加载失败时有明确错误提示（不崩主流程）

### 初步接口设计（提案）

```python
# core/plugins/models/svm_plugin.py
from core.interfaces import ModelBuilder

class SVMPlugin(ModelBuilder):
    name = "SVM"  # CLI 调用名
    params = {"C": 1.0, "kernel": "rbf"}  # 默认超参数

    def build(self, **kwargs):
        from sklearn.svm import SVC
        return SVC(**{**self.params, **kwargs})

    def hyperparameter_space(self):
        return {
            "C": [0.1, 1.0, 10.0],
            "kernel": ["linear", "rbf", "poly"]
        }
```

### 风险
- 插件接口稳定性（v7 内部可能变更，不算 breaking change）
- 依赖注入时机（CLI parse 后加载 vs 模块 import 时加载）

---

## DoD #2 详细设计：数据集边界验证

### 目标
处理真实使用中的边界数据情况，不让用户面对无意义的 traceback。

### 验收标准
| 场景 | 期望行为 |
|------|---------|
| 空数据集 X=[] | `Error: Dataset is empty. Provide at least 2 samples.` |
| 单类数据集（y 只有 1 个类别） | `Error: Only 1 class found in labels. Need at least 2 classes for classification.` |
| X 和 y 长度不匹配 | `Error: X and y have mismatched lengths: X.shape[0]=N, len(y)=M` |
| 极端值（全为 NaN/Inf） | `Error: Dataset contains only NaN or Inf values. Please check your data.` |

### 实现位置
- CLI: `core/cli.py` 或 `core/validation.py`（新增）
- API: `api/` 路由层统一拦截
- 单元测试: `tests/test_validation.py`（新增）

---

## DoD #3 详细设计：错误信息改进

### 目标
CLI 和 API 的错误输出从「Python traceback」变为「人类可读 + 行动建议」。

### 改进示例

| 场景 | Before（traceback） | After（友好） |
|------|---------------------|---------------|
| 未知模型名 | `KeyError: 'unknown-model'` | `Error: Unknown model 'unknown-model'. Available: SVM, Tree, KNN, MLP. Run with --list-models to see all.` |
| 无效超参数 | `ValueError: C must be positive` | `Error: Invalid value for --C: -1. C must be a positive number. Example: --C 1.0` |

### 实现位置
- `core/exceptions.py`（新增统一异常类）
- `core/cli.py`（CLI 入口统一错误处理）
- `api/` 路由层（统一错误格式化）

---

## DoD #4：C4 pytest 超时修复

### 问题描述
pytest 完整套件运行时间过长（> 60s），已知原因是 sklearn MLP 在某些测试中收敛慢。

### 诊断步骤
1. `pytest -v --durations=10` 找出最慢的 10 个测试
2. 确认是否确实是 MLP 相关测试
3. 如果是：为 MLP 测试添加 `@pytest.mark.slow` 标记，允许 CI/本地分开运行
4. 如果不是：继续诊断

### 验收标准
- 快速套件（无 `slow` 标记）能在 30s 内完成
- MLP 相关测试被标记，不阻塞常规 CI

---

## 版本历史

- v2 (2026-06-02): DoD #1 complete — PR#50 merged
  - core/interfaces.py: ModelBuilder 抽象接口
  - core/plugins/registry.py: 插件发现与注册
  - core/plugins/models/svm_plugin.py: SVM 插件示例
  - core/train_utils.py: build_model() 插件感知
  - tests/test_plugins.py: 15 tests pass
- v1 (2026-06-01): Initial — v7 DoD 细化，基于 ADR-0010 方向展开