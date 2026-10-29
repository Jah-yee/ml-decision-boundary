# REPRODUCE.md — ml-decision-boundary 复现指南

**版本**: v1.0 (v123 晚场)
**最后验证**: 2026-10-28 21:30 CST
**覆盖**: v12 SDK + v13 Experiment Provenance & Reproducibility

---

## 目录

1. [环境与安装](#环境与安装)
2. [质量关卡 P0–P3](#质量关卡-p0p3)
3. [v12 Python SDK](#v12-python-sdk)
4. [v13 实验来源（Provenance）](#v13-实验来源provenance)
5. [v13 重放（Replay）](#v13-重放replay)
6. [v13 覆盖率看板](#v13-覆盖率看板)
7. [v13 产物兼容性](#v13-产物兼容性)
8. [v13 内容寻址存储](#v13-内容寻址存储)
9. [v13 完整性守卫](#v13-完整性守卫)
10. [CLI 命令速查](#cli-命令速查)
11. [HTTP API 契约](#http-api-契约)
12. [故障排查](#故障排查)

---

## 环境与安装

### 要求

- Python 3.8–3.12
- pip
- scikit-learn ≥ 1.3.0（v13 兼容层支持 1.4.1–1.7.2）

### 安装

```bash
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary
pip install -r requirements.txt
```

### 验证安装

```bash
python3 -m compileall .
python3 -c "import main; print('main OK')"
python3 -c "from ml_db import MLDB; print('SDK OK')"
python3 -c "from core.provenance import build_provenance; print('provenance OK')"
python3 -c "from core.replay_guard import integrity_report; print('replay_guard OK')"
python3 -c "from core.compat import apply_shims; apply_shims(); print('compat OK')"
```

---

## 质量关卡 P0–P3

### P0 — 编译与导入（每次 commit 前必跑）

```bash
python3 -m compileall -q .
python3 -c "import main; print('OK')"
python3 -c "from ml_db import MLDB; print('OK')"
python3 -c "from core.replay_guard import integrity_report; print('OK')"
python3 -c "from core.compat import apply_shims; apply_shims(); print('OK')"
```

### P1 — 单元测试

```bash
python3 -m pytest -q --tb=short
```

**当前基线**: 612 passed / 5 skipped / 0 FAILED（v123 早场，362.69s）

### P2 — 基准冒烟

```bash
python3 -m benchmarks --quick
```

**当前基线**: Accuracy 0.7900 ≥ Threshold 0.7000 → ✅ PASSED

### P3 — HTTP 契约

```bash
# 启动 Web 服务
PYTHONPATH=. python3 web/server.py

# 健康检查
curl http://localhost:5000/api/health
# → {"status":"ok"}

# 完整性审计（全量）
curl "http://localhost:5000/api/provenance?integrity=1"
# → 200 + 审计报告

# 完整性审计（单模型）
curl "http://localhost:5000/api/provenance?integrity=1&id=<model_id>"
# → 200 + 单模型 verdict；404 如果模型不存在

# 执行验证
curl "http://localhost:5000/api/provenance?verify=1&id=<model_id>"
# → 200 + 执行结果；400 如果缺 id

# 批量预测
curl -X POST http://localhost:5000/api/predict/batch \
  -H "Content-Type: application/json" \
  -d '{"model":"SVM","dataset":"circles","points":[[1,2],[3,4]]}'
# → 200 + predictions 数组
```

---

## v12 Python SDK

### 概述

v12 在 `ml_db/` 包下提供了 Python 原生 SDK，支持同步和异步训练、模型版本化、标签批量查询。

### 安装与导入

```python
from ml_db import MLDB

# 连接默认 registry
db = MLDB()

# 连接指定 registry
db = MLDB(registry_base="/path/to/registry")
```

### 同步训练

```python
from ml_db import MLDB

db = MLDB()
result = db.train(
    model_type="SVM",
    dataset="circles",
    params={"kernel": "rbf", "C": 1.0, "gamma": "scale"},
    seed=42,
)
print(f"Accuracy: {result.accuracy:.4f}")
print(f"Model ID: {result.model_id}")
```

### 异步训练

```python
from ml_db import MLDB

db = MLDB()

# 提交异步任务
task = db.train_async(
    model_type="MLP",
    dataset="xor",
    params={"hidden_layer_sizes": (100, 50)},
    seed=42,
)
print(f"Task ID: {task.task_id}")

# 轮询状态
status = db.get_task(task.task_id)
print(f"Status: {status.status}")

# 等待完成
result = db.wait_for_task(task.task_id, timeout=300)
print(f"Accuracy: {result.accuracy:.4f}")
```

### 模型查询

```python
from ml_db import MLDB

db = MLDB()

# 列出所有模型
models = db.list_models(limit=10)

# 按标签查询
models = db.list_models_by_tags(["production", "v2"], match="any")

# 版本化查询
v1 = db.get_model_version("model_family_key", 1)
v2 = db.get_model_version("model_family_key", 2)
```

---

## v13 实验来源（Provenance）

### 概述

v13 为每个注册模型记录完整的实验来源：随机种子、数据集参数、超参数、环境版本、Git commit、规范指纹。两个模型是否"同条件产生"可以被机器验证。

### 来源记录

```python
from ml_db import MLDB

db = MLDB()

# 查看单模型来源
provenance = db.get_provenance("model_id")
print(json.dumps(provenance, indent=2))
```

**来源字段**:

| 字段 | 说明 |
|------|------|
| `seed` | 随机种子 |
| `dataset` | 数据集名称与参数 |
| `hyperparameters` | 解析后的超参数 |
| `environment` | Python / numpy / scikit-learn / joblib 版本 |
| `git_commit` | 训练时的 Git commit hash |
| `fingerprint` | 规范 JSON + SHA-256（前 16 hex） |

### 指纹设计

指纹**覆盖**：seed / dataset / hyperparameters / 环境版本 / git commit

指纹**不覆盖**：`captured_at`、`git.dirty`、`git.branch`、`environment.platform`

> 原因：这些是采集上下文而非复现条件，避免"指纹相同但记录不同"的语义冲突。

### 来源比较

```python
from ml_db import MLDB

db = MLDB()

# 比较两个模型的来源差异
diff = db.compare_provenance("model_id_a", "model_id_b")
for d in diff:
    print(f"{d['field']}: {d['left']} vs {d['right']}")
```

### 旧模型兼容

v13 之前的模型**无需迁移**。读取时返回空 provenance `{}`，不重写原 JSON。

---

## v13 重放（Replay）

### 概述

v13 为每个模型附带可执行重放方案，包含 SDK 精确片段、CLI 命令、依赖锁定摘要。

### 重放方案

```python
from ml_db import MLDB

db = MLDB()

# 获取重放方案
plan = db.replay_plan("model_id")
print(json.dumps(plan, indent=2))
```

**方案结构**:

```json
{
  "sdk": "MLDB.train(model_type='SVM', dataset='circles', params={'kernel':'rbf','C':1.0}, seed=42)",
  "cli": "python3 main.py --model SVM --dataset circles --seed 42 --params 'kernel=rbf,C=1.0'",
  "exact": true,
  "dependencies": {
    "available": true,
    "digest": "a1b2c3d4e5f6",
    "pinned_count": 4
  },
  "expected": {
    "fingerprint": "abc123def456"
  }
}
```

### 重放执行

```python
from ml_db import MLDB

db = MLDB()

# 实际执行重放
result = db.replay("model_id", register=False)
print(f"Reproduced: {result.reproduced}")
print(f"Fingerprint match: {result.fingerprint_match}")
print(f"Accuracy diff: {result.accuracy_diff}")
```

### 重放诚实性

- **SDK 路径**：始终精确，使用 `MLDB.train(...)` 的 Python 片段
- **CLI 路径**：仅当所有超参都能无损往返且 `test_size` 为默认值时标记 `exact: true`
- **禁止**在 CLI 路径声称"精确"而实际会产出不同模型

> 实测：`--params 'hidden_layer_sizes=(50,)'` 会把 `(50,)` 当成字符串传给 sklearn，静默训练出不同模型。CLI 路径会对此发出警告。

---

## v13 覆盖率看板

### 概述

v13 将"哪些模型可重放"从主观判断变为可查询的机器审计。4 类状态分类 + 阻塞原因分组。

### 分类状态

| 状态 | 含义 |
|------|------|
| `replayable_exact` | 有 provenance + CLI 可精确重放 |
| `replayable_sdk` | 有 provenance + 需走 SDK 重放 |
| `provenance_only` | 有 provenance 但缺少重放方案 |
| `no_provenance` | v13 前注册，无来源记录 |

### 查询覆盖率

```python
from ml_db import MLDB

db = MLDB()

# 全量覆盖率
summary = db.coverage_summary()
print(f"Total: {summary['total']}")
print(f"Coverage: {summary['coverage_pct']}%")
print(f"Replayable: {summary['replayable_pct']}%")

# 阻塞原因分组
report = db.replayability_report()
for r in report:
    print(f"{r['reason']}: {r['count']} models")
```

### CLI 覆盖率看板

```bash
python3 main.py model coverage
```

输出示例：
```
📊 Provenance Coverage — 21965 registered model(s)
============================================================
   ✅ Replayable (exact CLI):     1032
   🟡 Replayable (SDK only):       77
   📋 Provenance only:              0
   ❌ No provenance:           20856

   Coverage: 5.04% | Replayable: 5.04% | CLI exact: 4.70%

   Top blocking reasons:
   1. pre-v13 registry: 20856 models
```

---

## v13 产物兼容性

### 问题

sklearn 1.4.1 → 1.7.2 升级导致 700 个 GradientBoostingClassifier 产物无法加载。根因在**字节级**：pickle 的 `STACK_GLOBAL` 操作码把 Cython 内部名 `__pyx_unpickle_CyHalfBinomialLoss` 写进了字节流，而 sklearn 1.7.2 改名为公开的 `CyHalfBinomialLoss`，旧名消失。

### 解法

`core/compat.py`（唯一实现源）：一张"旧名 → 新名"别名表，在反序列化时把旧名挂回模块上。

```python
_ALIASES = (
    ("sklearn._loss._loss", "__pyx_unpickle_CyHalfBinomialLoss", "CyHalfBinomialLoss"),
)
```

`apply_shims()` 在导入时自动执行（`core.registry` 与 `core.blob_store` 都 import 它），幂等、不会重复安装、模块缺失时静默跳过。

### 设计约束

- **不改写任何产物字节**：shim 只作用于 unpickle 时刻
- **不改写元数据 JSON**：与 v13 DoD #3 的只读保证一致
- **不吞掉 `InconsistentVersionWarning`**：该警告是有信息量的 —— 产物是用另一个库版本拟合的，其数值行为不保证一致

### 健康审计

```python
from ml_db import MLDB

db = MLDB()
health = db.health(sample=100)
print(f"Loadable: {health['loadable']}")
print(f"Metadata only: {health['no_artifact']}")
print(f"Unloadable: {health['unloadable']}")
```

CLI：
```bash
python3 main.py model health --sample 100
```

**实测**：700/700 全部恢复，可加载 14059 → 14759，不可加载 700 → 0。

---

## v13 内容寻址存储

### 概述

v13 将 registry 产物从 per-model 布局迁移到 SHA-256 寻址 blob store，实现跨模型去重。

### 迁移

```bash
python3 scripts/migrate_to_blob_store.py
```

**实测**：14368 模型记录迁移，250 唯一 blob，**3.9GB 回收**（4.0G → 180M）。

### 存储统计

```python
from ml_db import MLDB

db = MLDB()
stats = db.storage_stats()
print(f"Total models: {stats['total_models']}")
print(f"Unique blobs: {stats['unique_blobs']}")
print(f"Storage size: {stats['storage_size']} bytes")
print(f"Dedup ratio: {stats['dedup_ratio']}x")
```

CLI：
```bash
python3 main.py model storage
```

---

## v13 完整性守卫

### 概述

v13 DoD #4：冻结的 replay recipe 漂移分级。用三段式分级取代布尔相等比较。

### 分级

| 级别 | 含义 | 判据 |
|------|------|------|
| `none` | recipe 与今日代码输出一致 | 字符串完全相同 |
| `cosmetic` | 拼写不同，指同一次运行 | 超参值语义等价 + run-defining flag 相同 |
| `semantic` | 会训出不同的模型 | 超参值不同 或 run-defining flag 不同 |

### 三个关键判据

1. **超参值语义归一化** —— `(50,)` 与 `[50]` 归一为同一 tuple；`50` 与 `50.0` 归一为同一数值
2. **run-defining flag 与 visual-only flag 分离** —— `--n-samples` / `--noise` 不进入 CLI 训练路径，二者不同是 cosmetic 而非 semantic
3. **`--params` 排除出 flag 比较** —— 避免仅因参数顺序不同而误报

### 完整性审计

```python
from ml_db import MLDB

db = MLDB()
report = db.replay_integrity()
print(f"Total: {report['total']}")
print(f"Current: {report['recipe_current']}")
print(f"Cosmetic: {report['cosmetic_drift']}")
print(f"Semantic: {report['semantic_drift']}")
print(f"Broken: {report['broken']}")
```

CLI：
```bash
python3 main.py model integrity
```

**实测（21965 模型）**：
- ✅ Recipe current: 21553
- 🟡 Cosmetic drift: 412（拼写差异，同一运行）
- ❌ Semantic drift: 0（不会训出不同模型）
- 🔒 Broken: 0（可复现性承诺未破）

### 执行验证

```python
from ml_db import MLDB

db = MLDB()
verdict = db.verify_replay("model_id")
print(f"Verdict: {verdict}")
```

CLI：
```bash
python3 main.py model verify <model_id>
```

> 漂移审计说"recipe 是否还匹配代码"，只有执行才说"运行是否还复现"。

---

## CLI 命令速查

### 模型管理

```bash
# 列出模型
python3 main.py model list [--limit N] [--tag TAG]

# 检查单模型
python3 main.py model inspect <model_id>

# 来源与差异
python3 main.py model provenance <model_id>
python3 main.py model diff <model_id_a> <model_id_b>

# 重放
python3 main.py model replay <model_id>           # 打印重放方案
python3 main.py model replay <model_id> --run     # 实际执行重放

# 覆盖率看板
python3 main.py model coverage

# 存储统计
python3 main.py model storage

# 健康审计
python3 main.py model health [--sample N]

# 完整性审计
python3 main.py model integrity

# 执行验证
python3 main.py model verify <model_id>

# 标签管理
python3 main.py model tag <model_id> <tag_name>
python3 main.py model untag <model_id> <tag_name>
python3 main.py model tags
python3 main.py model list --tags a b c --match any
```

### 训练与实验

```bash
# 单次实验（自动注册）
python3 main.py --dataset circles --model SVM --seed 42

# 不注册的实验
python3 main.py --dataset circles --model SVM --no-registry

# 全量实验矩阵
python3 main.py --all
```

### 基准测试

```bash
# 快速冒烟
python3 -m benchmarks --quick

# 全量套件
python3 -m benchmarks

# 树深度扫描
python3 -m benchmarks --depth-sweep

# 超参扫描
python3 -m benchmarks --hyperparam-sweep
```

---

## HTTP API 契约

### 基础地址

```
http://localhost:5000
```

### 健康检查

```
GET /api/health
→ 200 {"status":"ok"}
```

### 来源与重放

```
GET /api/provenance?integrity=1                    # 全量完整性审计
GET /api/provenance?integrity=1&id=<model_id>      # 单模型完整性
GET /api/provenance?verify=1&id=<model_id>         # 执行验证
GET /api/provenance?coverage=1                     # 覆盖率看板
```

**状态码**：
- 200 — 成功
- 400 — 缺少必需参数（如 `verify` 缺 `id`）
- 404 — 模型不存在
- 500 — 内部错误

### 模型注册表

```
GET /api/registry?limit=N              # 列出模型
GET /api/registry?tag=TAG              # 按标签过滤
GET /api/registry?tags=a,b,c&match=any # 批量标签查询
GET /api/registry?family=KEY           # 按版本族查询
```

### 训练与预测

```
POST /api/train              # 同步训练
POST /api/train_async        # 异步训练
GET  /api/tasks              # 任务列表
GET  /api/tasks/<task_id>    # 任务状态
POST /api/predict/batch      # 批量预测
```

**批量预测请求体**：
```json
{
  "model": "SVM",
  "dataset": "circles",
  "points": [[0.1, 0.2], [0.3, 0.4]]
}
```

**批量预测响应**：
```json
{
  "model": "SVM",
  "dataset": "circles",
  "params": {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
  "predictions": [1, 0],
  "count": 2
}
```

---

## 故障排查

### matplotlib 后端（serverless 环境）

```python
import matplotlib
matplotlib.use('Agg')  # 必须在导入 pyplot 之前
```

所有入口点（`main.py`、`api/train.py`、`web/server.py`）已内置此处理。

### scikit-learn 版本不匹配

```bash
pip show scikit-learn | grep Version
# 当前基线: 1.7.2
# v13 兼容层支持 1.4.1–1.7.2
```

### 产物加载失败

```python
from core.compat import apply_shims
apply_shims()  # 在加载任何产物之前调用

import joblib
model = joblib.load("path/to/model.joblib")
```

### MLP 训练缓慢

MLP 使用 `max_iter=2000`。开发时可临时调低：
```python
# 在 core/train_utils.py 中设置 max_iter=200
```

### pytest 超时

```bash
timeout 600 pytest tests/ -q --tb=short
```

### 导入错误

验证核心模块可导入：
```bash
python3 -c "from core.datasets import DATASET_GENERATORS; print('OK')"
python3 -c "from core.train_utils import build_model; print('OK')"
python3 -c "from core.provenance import build_provenance; print('OK')"
python3 -c "from core.replay_guard import integrity_report; print('OK')"
python3 -c "from core.compat import apply_shims; apply_shims(); print('OK')"
python3 -c "from core.blob_store import BlobStore; print('OK')"
python3 -c "from core.coverage import provenance_coverage; print('OK')"
```

### Registry 体积

当前 registry 体积：184M（v13 内容寻址存储迁移后，从 4.0G 回收）。

```bash
python3 main.py model storage
```

---

## CI / 可复现性

- **Python**: 3.8–3.12（当前 3.12）
- **随机种子**: 固定为 42（所有模型训练可复现）
- **依赖锁定**: `requirements.lock`（pip-compile 生成，已提交）
- **CI 流水线**（`.github/workflows/ci.yml`）：
  - P0: compileall smoke
  - P1: pytest（612 tests）
  - P2: benchmark smoke（`benchmarks --quick`）
  - P3: API/health 契约

---

*最后验证: 2026-10-28 21:30 CST (v123 晚场)*
*维护人: 太子*