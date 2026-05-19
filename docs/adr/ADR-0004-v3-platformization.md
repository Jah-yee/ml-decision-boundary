# ADR-0004 — v3 平台化决策：core/ 模块提取

**日期**: 2026-05-19
**状态**: Accepted (PR#36 merged 2026-05-19)
**决策者**: Jah-yee <jydu_seven@outlook.com>

---

## 背景

v3 Platform 阶段的核心目标是消除代码重复、建立统一模块化架构。启动时存在三个入口点：

- `CLI` — `main.py`
- `Web` — `web/server.py`
- `API` — `api/train.py`

三个入口点各自实现了类似的 dataset generators、model factories 和 train utilities，造成约 360 行重复代码（主要在 `api/train.py` 和 `web/server.py` 之间）。

### 重复问题详情

| 重复模块 | api/train.py | web/server.py | main.py |
|---------|-------------|--------------|---------|
| Dataset generators (make_circles, make_moons, make_blobs, make_xor, make_s_curve) | ~130 行 | ~130 行 | 独有副本 |
| Model factory (build_model) | ~30 行 | ~30 行 | 独有副本 |
| Train utilities (slider_to_params, compute_boundary_grid, get_model_info_dict) | ~60 行 | ~60 行 | 独有副本 |
| **合计** | ~224 行 | ~271 行 | 独有 |

这导致：
- 维护成本高：修改一处可能需要同步修改多处
- 测试覆盖率低：重复代码无法有效复用测试
- 代码不一致风险：blobs 参数差异（见下方 open issue）

---

## 决策

提取共享代码到 `core/` 模块，结构如下：

```
core/
├── __init__.py
├── datasets.py     # 5 个 dataset generators + DATASET_GENERATORS dict
└── train_utils.py  # 4 个 utilities
```

### `core/datasets.py`

```python
# 5 个 generator 函数：
make_circles(n_samples=300, noise=0.1, seed=42)
make_moons(n_samples=300, noise=0.15, seed=42)
make_blobs(n_samples=300, centers=3, cluster_std=1.5, seed=42)
make_xor(n_samples=300, noise=0.15, seed=42)
make_s_curve(n_samples=300, noise=0.1, seed=42)

# 统一 dict
DATASET_GENERATORS = {
    "circles": make_circles,
    "moons": make_moons,
    "blobs": make_blobs,
    "xor": make_xor,
    "s_curve": make_s_curve,
}
```

### `core/train_utils.py`

```python
def build_model(model_type: str, **kwargs) -> sklearn.base.BaseEstimator
def slider_to_params(model_type: str, complexity: float) -> dict
def compute_boundary_grid(X: np.ndarray, model, resolution=100) -> tuple[np.ndarray, np.ndarray, np.ndarray]
def get_model_info_dict(model) -> dict
```

### 依赖注入方案

为避免直接 `import core` 造成测试耦合，采用基于 dict 的注入：

```python
# 入口点通过参数接收 generators
def train(dataset_generators: dict, build_model_fn, ...):
    X, y = dataset_generators[dataset_name](**params)
    model = build_model_fn(model_type, **model_params)
```

已在 `api/train.py` 和 `web/server.py` 中实现此模式。

---

## 后果

### 代码行数变化

| 文件 | 重构前 | 重构后 | 减少 |
|------|--------|--------|------|
| api/train.py | ~224 行 | ~63 行 | **-161 行** |
| web/server.py | ~271 行 | ~100 行 | **-171 行** |
| main.py | 不变 | 不变 | — (保留独立副本作为 CLI 快速入口) |
| core/ 新增 | 0 | ~240 行 | — |
| **总计** | ~495 行 | ~403 行 | **-92 行净减少** |

### 已发现 Open Issue：Blobs Semantic Difference

重构过程中发现 `main.py` 和 `core/datasets.py` 中 `make_blobs` 调用存在语义差异：

- **main.py**：`make_blobs(centers=2, ...)` — 2 类
- **core/datasets.py**（原 api/train.py/web/server.py）：`make_blobs(centers=3, ...)` — 3 类

**影响**：同一 `blobs` 数据集在 CLI vs Web/API 中语义不同。此问题尚未修复，记录于此 ADR 作为已知问题，需在后续 PR 中统一。

### Positive Consequences

- ✅ 代码重复从 ~360 行降至 ~0 行（入口点之间）
- ✅ 统一数据集语义可通过单一修复解决
- ✅ `core/` 模块可独立测试
- ✅ 新增数据集或模型只需修改一处

### Negative Consequences

- ⚠️ `main.py` 暂保留独立副本，与 `core/` 不同步（CLI 快速入口优先，保持 zero-config）
- ⚠️ blobs 语义差异需后续修复
- ⚠️ 引入间接层，调试时需多跳（但可通过直接 import core 快速定位）

### Status

- **Proposed**: 文档已创建，PR#36 准备中
- **待合并**: PR#36 合并后状态更新为 Accepted

---

## 下一步

1. PR#36 合并后，更新状态为 `Accepted`
2. 修复 blobs 语义差异（统一 centers=3 或参数化）
3. 考虑将 `main.py` 也迁移到 `core/`（消除最后的重复）
4. 为 `core/` 目录添加单元测试

---

## 参考

- ADR-0003: Phase v2 → v3 升级判定（2026-05-08）
- `core/datasets.py` — 新增数据集模块
- `core/train_utils.py` — 新增训练工具模块
- `api/train.py` — 重构示例（~224→63 行）
- `web/server.py` — 重构示例（~271→100 行）