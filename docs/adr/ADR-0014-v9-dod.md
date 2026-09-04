# ADR-0014 — v9 DoD 细化：Documentation, Examples & Registry UX

**日期**: 2026-07-05
**状态**: ✅ Accepted（2026-07-08 太子代 Accept，v9 DoD #1-4 全部完成）
**维护人**: 太子

---

## 背景

v8 Model Registry & Lifecycle（ADR-0013）已于 2026-07-04 完成并 Accepted。v9 主题定位为**文档 & 示例 + Registry UX 增强**，解决以下技术债：
- **C8**: 文档示例不足 — 新用户上手困难
- **C9**: Web UI 功能有限 — 交互式体验差

v9 不做大型架构变更，聚焦于让现有功能更易用、更可达。

---

## v9 主题

**Documentation, Examples & Registry UX**

---

## v9 DoD 细化

| # | DoD 项目 | 描述 | 优先级 |
|---|---------|------|--------|
| 1 | **示例脚本集** | 新增 3+ 个独立可运行的 example 脚本，覆盖 SVM/KNN/MLP 等常见场景，复制即跑 | P1 |
| 2 | **Cookbook 文档** | 编写 `docs/cookbook.md`，覆盖：快速上手、模型选择指南、Registry 使用教程、自定义插件开发 | P1 |
| 3 | **Registry CLI 增强** | `ml-db model compare <id1> <id2>` — 对比两次注册的模型精度；`ml-db model tag <id> --tag <name>` — 打标签 | P1 |
| 4 | **README 改进** | 更新 README：增加 Quick Start（5行内跑起来）、v8/v9 功能徽章、Architecture 图 | P1 |
| 5 | **ADR-0014 Accepted 后同步** | 将本 DoD 同步至 `NEXT_ROUND_THEME.md` + `phases.md` | P0 |

---

## DoD #1 详细设计：示例脚本集

### 目标
让新用户在 5 分钟内跑通第一个决策边界可视化，建立对工具的第一印象。

### 目录结构

```
examples/
├── 01_quick_start.py      # 5 行代码，circles + SVM
├── 02_model_comparison.py  # 同一数据集上对比 SVM/Tree/KNN
├── 03_custom_model.py     # 使用自定义插件模型
├── 04_registry_usage.py   # 使用 Model Registry 管理实验
└── 05_benchmark_harness.py # 跑 benchmark 并解读报告
```

### 验收标准

| 文件 | 运行命令 | 预期产出 |
|------|---------|---------|
| `01_quick_start.py` | `python examples/01_quick_start.py` | `output/` 下生成 PNG |
| `02_model_comparison.py` | `python examples/02_model_comparison.py` | 4 模型对比图 |
| `03_custom_model.py` | `python examples/03_custom_model.py` | 插件模型可视化 |
| `04_registry_usage.py` | `python examples/04_registry_usage.py` | 模型注册到 registry |
| `05_benchmark_harness.py` | `python examples/05_benchmark_harness.py --quick` | 生成 benchmark 报告 |

### 实现要求
- 所有脚本在 Python 3.10+ 下运行，无需额外依赖（requirements.txt 已覆盖）
- 每个脚本顶部有 docstring 说明目的、依赖、输出
- 示例数据使用内置 datasets，不依赖外部数据

---

## DoD #2 详细设计：Cookbook 文档

### 目标
为有经验的 ML 工程师提供"按需查阅"的实用指南，解决"文档示例不足"（C8）。

### 文档结构（`docs/cookbook.md`）

```markdown
# ml-decision-boundary Cookbook

## 快速上手
## 模型选择指南
## 使用 Model Registry
## 编写自定义插件
## 解读 Benchmark 报告
## FAQ / 故障排查
```

### 各节内容要求

**快速上手**（~100行 markdown）
- 安装步骤
- 运行第一个实验
- 理解输出（PNG + JSON）
- 常见错误

**模型选择指南**（~150行 markdown）
- 什么时候用 SVM vs Tree vs KNN vs MLP
- 超参数对决策边界的影响（配图说明）
- 针对不同数据集（circles/moons/blobs/xor）的推荐模型

**使用 Model Registry**（~120行 markdown）
- `ml-db model list` / `inspect` / `delete` 使用示例
- `~/.ml-decision-boundary/registry/` 目录结构说明
- 如何用 registry 追踪实验迭代

**编写自定义插件**（~150行 markdown）
- 继承 `base.py` 的 `BaseModelPlugin` 接口
- 实现 `train()`, `visualize()`, `get_state()`, `load_state()`
- 注册插件的两种方式（CLI flag / 代码）

**解读 Benchmark 报告**（~100行 markdown）
- JSON schema 说明
- regression detection 逻辑
- 如何设置 accuracy threshold

**FAQ / 故障排查**（~80行 markdown）
- 常见错误码及解决方案
- `pytest` 超时问题处理
- 序列化兼容性说明

### 验收标准
1. `docs/cookbook.md` 存在且每个章节字数 ≥ 上述估算
2. `python3 -m pytest docs/ -q` 无错误（无测试，但检查无语法错误）
3. Cookbook 可在 GitHub Markdown 渲染器中正常显示

---

## DoD #3 详细设计：Registry CLI 增强

### 目标
在 v8 Registry 基础上增加模型对比和标签功能，提升实验追踪体验。

### 新增 CLI 命令

```bash
# 对比两个模型的精度（来自 registry）
ml-db model compare <model_id_1> <model_id_2>

# 给模型打标签（如 "best-for-circles", "baseline-v1"）
ml-db model tag <model_id> --tag <tag_name>
ml-db model tag <model_id> --remove-tag <tag_name>

# 按标签过滤列表
ml-db model list --tag <tag_name>

# 列出所有标签
ml-db model tags
```

### Registry 元数据扩展（tags 字段）

```json
// ~/.ml-decision-boundary/registry/models/<id>.json 新增字段
{
  "id": "2026-07-05_abc123",
  "tags": ["best-for-circles", "baseline-v1"],
  ...
}
```

### RegistryManager 扩展方法

```python
# core/registry.py — 新增方法

    def tag_model(self, model_id: str, tag: str) -> None:
        """给模型打标签"""

    def untag_model(self, model_id: str, tag: str) -> None:
        """移除模型的标签"""

    def list_tags(self) -> Dict[str, List[str]]:
        """返回 {tag: [model_ids]} 的反向索引"""

    def compare_models(self, model_id_1: str, model_id_2: str) -> Dict[str, Any]:
        """
        对比两个模型的精度，输出表格化 diff。
        返回: {model1: {...}, model2: {...}, differences: [...]}
        """
```

### 验收标准

| 命令 | 预期行为 |
|------|---------|
| `ml-db model compare <id1> <id2>` | 输出两个模型在同数据集上的精度对比表 |
| `ml-db model tag <id> --tag foo` | 成功提示；`inspect` 可看到 tags 字段 |
| `ml-db model list --tag foo` | 只列出含 `foo` 标签的模型 |
| 未知 model_id | 友好错误：`Model '<id>' not found.` |

---

## DoD #4 详细设计：README 改进

### 目标
让新用户 5 分钟内了解工具价值并跑起来；同时展示 v8/v9 能力。

### 新增内容

**Quick Start 区块**（新增，在 Usage 之前）
```markdown
## ⚡ Quick Start

pip install -e .
python3 main.py          # 默认 circles + SVM
ml-db model list         # 查看注册模型
python3 -m benchmarks --quick   # 运行 benchmark
```

**Architecture 图**（新增，使用 ASCII/ mermaid）
```markdown
## Architecture

[main.py] → [core/train.py] → [core/plugins/] → [output/]
                    ↓
            [core/registry.py] → [~/.ml-decision-boundary/registry/]
```

**功能徽章**
```markdown
[![v8 Model Registry](https://img.shields.io/badge/v8-Model%20Registry-green)]
[![v9 Documentation](https://img.shields.io/badge/v9-Documentation-blue)]
```

**API 使用示例**（新增）
```python
from core.registry import get_registry_manager
rm = get_registry_manager()
models = rm.list_models()
print(f"Registered {len(models)} models")
```

### 验收标准
1. README 有 `⚡ Quick Start` 区块
2. README 有 Architecture 区块
3. `python3 -m compileall .` 无新增 warning/error（README 改动不影响编译）
4. README 与 `spec/CHARTER.md` 保持一致（无矛盾描述）

---

## 版本历史

- v1 (2026-07-05): Initial draft — v9 DoD 细化，Documentation & Registry UX

---

## 待皇上批准

1. v9 主题方向是否合适？（Documentation + Registry UX）
2. 5 个 DoD 项目是否在两周内可完成？
3. 是否有其他优先级更高的 v9 方向？

---

## 技术债务追踪（v9 解决项）

| # | 问题 | 解决方式 |
|---|------|---------|
| C8 | 文档示例不足 | DoD #1（示例脚本）+ DoD #2（Cookbook）+ DoD #4（README 改进） |
| C9 | Web UI 功能有限 | 📋 v10 候选（本期不承诺） |
