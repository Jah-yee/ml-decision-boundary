# ADR-0013 — v8 DoD 细化：Model Registry & Lifecycle

**日期**: 2026-06-07
**状态**: Accepted
**Accepted 日期**: 2026-07-04
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
| 4 | **Benchmark Registry** | benchmark 输出自动注册到 registry；结构化 JSON 含 run_id/timestamp/duration/model_results/git_hash；`list_benchmarks()` / `get_benchmark()`；CLI `ml-db benchmark list` / `inspect <id>`；基于 registry 的回归检测；`benchmarks/run.py` 集成 `--registry` flag | P1 | 对应 C6 技术债 |
| 5 | **ADR-0013 Accepted 后同步** | 将本 DoD 同步至 NEXT_ROUND_THEME.md | P0 | 元任务 |

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

---

## DoD #4 详细设计：Benchmark Registry

### 目标
benchmark 输出持久化到 registry，支持历史追溯和自动化回归检测。解决 C6 技术债："benchmark 输出无结构化 registry，回归检测依赖手动"。

### Registry 目录结构（扩展）

```
~/.ml-decision-boundary/registry/
├── models/
│   ├── 2026-06-07_abc123.json
│   └── ...
└── benchmarks/
    ├── 2026-06-07_xyz789.json   # 单次 benchmark run 的元数据
    └── ...
```

### 基准元数据 Schema（`benchmarks/*.json`）

```json
{
  "id": "2026-06-07_xyz789",
  "mode": "full",                   // "full" | "quick" | "depth_sweep" | "hyperparam_sweep"
  "timestamp": "2026-06-07T09:57:00+08:00",
  "duration_seconds": 12.34,
  "git_hash": "abc1234",             // 当前 git commit hash（不可用时为 "unknown"）
  "total_experiments": 90,
  "passed": 88,
  "failed": 2,
  "regressions": 0,
  "model_results": [
    {
      "dataset": "circles",
      "model": "SVM",
      "params": {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
      "accuracy": 0.974,
      "train_time": 0.012,
      "passed": true,
      "threshold": 0.70
    },
    {
      "dataset": "moons",
      "model": "Tree",
      "params": {"max_depth": 3},
      "accuracy": 0.820,
      "train_time": 0.008,
      "passed": true,
      "threshold": 0.70
    }
    // ... all experiment results
  ],
  "summary": {
    "avg_accuracy": 0.8912,
    "best_accuracy": 0.987,
    "worst_accuracy": 0.612,
    "avg_train_time": 0.034
  },
  "regression_details": [],          // 超参 sweep 模式下的回归详情
  "report_json": "benchmarks/reports/2026-06-07.json",
  "report_md": "benchmarks/reports/2026-06-07.md"
}
```

### 新增方法（`RegistryManager`）

```python
# core/registry.py

@dataclass
class BenchmarkMetadata:
    """Schema for a registered benchmark run."""
    id: str                          # 2026-06-07_xyz789
    mode: str                        # "full" | "quick" | "depth_sweep" | "hyperparam_sweep"
    timestamp: str                    # ISO8601 with timezone
    duration_seconds: float
    git_hash: str                    # git rev-parse HEAD, fallback "unknown"
    total_experiments: int
    passed: int
    failed: int
    regressions: int
    model_results: List[Dict[str, Any]]
    summary: Dict[str, Any]
    regression_details: List[Dict[str, Any]]
    report_json: str                 # relative path
    report_md: str                   # relative path


class RegistryManager:
    # ── DoD #4: Benchmark Registry ─────────────────────────────────────────

    def save_benchmark(
        self,
        mode: str,
        results: list,             # raw benchmark results list
        summary: dict,             # summary dict from run.py
        duration_seconds: float,
        report_json: str = "",
        report_md: str = "",
        regression_details: list = None,
    ) -> str:
        """
        Persist a benchmark run to the registry.

        Returns:
            benchmark_id: str, the unique ID (e.g. "2026-06-07_xyz789")
        """

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered benchmark runs, newest first.
        """

    def get_benchmark(self, benchmark_id: str) -> Dict[str, Any]:
        """
        Return full metadata for a specific benchmark run.
        Raises FileNotFoundError if not found.
        """

    def get_latest_benchmark(self, mode: str = None) -> Optional[Dict[str, Any]]:
        """
        Return the most recent benchmark run, optionally filtered by mode.
        Returns None if no benchmarks found.
        """

    def detect_regressions(
        self,
        current_results: list,
        latest_run_id: str,
        threshold: float = 0.05,
    ) -> List[Dict[str, Any]]:
        """
        Compare current_results against the latest registered run.
        Returns list of regression entries: {dataset, model, params,
        current_acc, previous_acc, drop_pct}.
        """
```

### CLI 设计

```bash
# 列出所有 benchmark runs
ml-db benchmark list

# 查看指定 benchmark run 详情
ml-db benchmark inspect <id>

# 对比两次 run（回归检测）
ml-db benchmark diff <run_id_1> <run_id_2>

# 删除指定 run
ml-db benchmark delete <id>
```

### CLI 输出示例

```
$ ml-db benchmark list

  ID                   Mode              Experiments  Passed  Regressions  Duration  Created
  ─────────────────────────────────────────────────────────────────────────────────────
  2026-06-16_a1b2c3    full              90           88      0            12.3s     2026-06-16T09:42:00+08:00
  2026-06-15_d4e5f6    hyperparam_sweep  180          175     2            48.7s     2026-06-15T18:30:00+08:00

$ ml-db benchmark inspect 2026-06-16_a1b2c3

  Mode:       full
  Git hash:   abc1234
  Duration:   12.3s
  Total:      90 | Passed: 88 | Failed: 2 | Regressions: 0
  Avg acc:    0.8912
  Best acc:   0.987 (SVM, circles)
  Worst acc:  0.612 (Tree, xor)
  Report:     benchmarks/reports/2026-06-16.json
```

### 回归检测流程

1. `benchmarks/run.py` 添加 `--registry` flag（默认开启）
2. 每次 benchmark run 结束后调用 `registry_manager.save_benchmark(...)`
3. 当传入 `--baseline-from-registry` flag 时，从 registry 加载最新 run 的 `model_results`，作为回归对比基准
4. `detect_regressions()` 逐条对比同一 (model, dataset, params) 的 accuracy，差值超过阈值（默认 5%）标记为回归

```python
# benchmarks/run.py — 集成示例
import argparse
...
parser.add_argument("--registry", action="store_true", default=True,
                    help="Auto-register results to ~/.ml-decision-boundary/registry/benchmarks/")
parser.add_argument("--no-registry", dest="registry", action="store_false",
                    help="Disable auto-registration")
parser.add_argument("--baseline-from-registry", action="store_true",
                    help="Use latest registered run as regression baseline")

def main():
    args = parser.parse_args()
    ...
    summary = run_benchmarks(quick=args.quick, depth_sweep=args.depth_sweep, ...)

    if args.registry:
        from core.registry import get_registry_manager
        rm = get_registry_manager()
        # 收集 model_results 列表（从 summary/results 中重建）
        run_id = rm.save_benchmark(
            mode=...,
            results=results,        # raw experiment list
            summary=summary,        # summary dict
            duration_seconds=elapsed,
            report_json=summary.get("json_report", ""),
            report_md=summary.get("md_report", ""),
        )
        print(f"  Registered: {run_id}")

    if args.baseline_from_registry:
        rm = get_registry_manager()
        latest = rm.get_latest_benchmark(mode="full")
        if latest:
            regressions = rm.detect_regressions(results, latest["id"])
            if regressions:
                print(f"  ⚠️  {len(regressions)} regressions detected vs {latest['id']}")
```

### 验收标准

| # | 标准 | 验证方式 |
|---|------|---------|
| 1 | `python3 -m benchmarks.run` 后 `~/.ml-decision-boundary/registry/benchmarks/` 下有对应 JSON | `ls ~/.ml-decision-boundary/registry/benchmarks/` |
| 2 | JSON 包含 `id`, `timestamp`, `mode`, `model_results[]`, `summary`, `git_hash` | 检查 JSON schema |
| 3 | `RegistryManager.list_benchmarks()` 返回按 `created_at` 倒序的列表 | 单元测试 |
| 4 | `RegistryManager.get_benchmark(id)` 找到指定 run | 单元测试 |
| 5 | `RegistryManager.detect_regressions()` 对比两次 run，正确标记差值 >5% 的项 | 单元测试 |
| 6 | `ml-db benchmark list` 输出表格，含 ID/Mode/Passed/Duration | CLI 集成测试 |
| 7 | `ml-db benchmark inspect <id>` 输出完整元数据 | CLI 集成测试 |
| 8 | `--no-registry` flag 禁用注册，不生成 registry 文件 | 手动验证 |
| 9 | `git_hash` 不可用时 fallback 为 "unknown" | 手动/测试 |

### 实现位置

- `core/registry.py`（`BenchmarkMetadata` dataclass + `save_benchmark` / `list_benchmarks` / `get_benchmark` / `get_latest_benchmark` / `detect_regressions` 方法）
- `benchmarks/run.py`（添加 `--registry` / `--no-registry` / `--baseline-from-registry` flags，集成 `save_benchmark` 调用）
- `core/cli.py`（扩展 `benchmark` 子命令：`list`, `inspect`, `diff`, `delete`）
- `tests/test_registry.py`（扩展 benchmark 相关测试用例）

### 技术风险

- **git_hash 不可用**：CI 环境中 `.git` 目录可能不存在，使用 try/except fallback "unknown"
- **registry 目录权限**：写入 `~/.ml-decision-boundary/` 需要 HOME 环境变量正常；需处理 `PermissionError` 并给出友好提示
- **大文件 registry**：每次 benchmark run 生成的 JSON 可能较大（hyperparam_sweep 数百条）；考虑对 `model_results` 按需加载（不在 `list_benchmarks` 中加载完整结果）