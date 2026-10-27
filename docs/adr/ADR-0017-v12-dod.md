# ADR-0017 — v12 DoD 细化：Python API & SDK Foundation

**日期**: 2026-10-07
**状态**: ✅ Accepted（DoD #1 ✅ / #2 ✅ / #3 ✅ / #4 ✅）
**维护人**: 太子
**更新**: 2026-10-25 (v119 晚场 — DoD #3 Registry 改进完成，DoD #4 验收通过)

---

## 背景

v11 Multi-Dataset Expansion & Experiment History（ADR-0016）— DoD #1-4 全部完成，ADR-0016 于 2026-10-25 Accepted（PR #58 merged）。v11 扩展了数据集支持、批预测 API 和实验历史追踪能力。

v12 主题定位为 **Python API & SDK Foundation**，为 ml-decision-boundary 建立清晰的 Python 编程接口，为外部集成和自动化流水线奠定基础。

---

## v12 主题

**Python API & SDK Foundation**

---

## v12 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | **Python SDK 接口** | 建立 `from ml_db import MLDB` 顶层 API，封装训练/预测/注册全流程 | P1 | ✅ (v119 早场) |
| 2 | **异步训练任务** | 后台训练任务 + 轮询状态 API，支撑长时间训练不被 HTTP 超时中断 | P1 | ✅ (v119 早场 #2) |
| 3 | **Registry 改进** | 模型版本化（v1/v2）+ 标签批量查询（CLI `--tags A B --match any\|all`；单标签 `--tag KEY` 保持不变） | P1 | ✅ (v119 晚场) |
| 4 | **ADR-0017 Accepted** | DoD #1-3 全部完成后，将 ADR-0017 状态更新为 Accepted | P0 | ✅ (v119 晚场) |

---

## 技术约束

- Python SDK 必须向后兼容现有 CLI 接口
- 异步训练需要持久化任务状态（重启不丢失）
- Registry 版本化需要向后兼容 v1 模型 ID 格式
- ADR-0017 Accepted 后方可开始 v13 规划

---

## 验收标准（DoD #4 完成后勾选）

- [x] ADR-0017 状态: Accepted（DoD #1-#4 全部完成）
- [x] P0: compileall + import smoke 通过 ✅ (v119 早场；v119 晚场复验 exit 0 + import OK)
- [x] P1: pytest -q 通过 ✅ 438 passed, 5 skipped, 0 FAILED (v119 晚场，424 → 438，+14 review 修复与 parity 测试)
- [x] SDK: `from ml_db import MLDB; m = MLDB()` 可实例化 ✅ (v119 早场)
- [x] SDK: `m.train(...)` 返回训练结果 ✅ (v119 早场)
- [x] SDK: `m.predict(...)` 返回预测结果 ✅ (v119 早场)
- [x] Async: 后台任务状态可轮询 ✅ (v119 早场 #2)
- [x] Registry: 模型版本可查询 ✅ (v119 晚场 — `family` / `version` / `get_model_versions()` / `get_latest_version()` / `list_model_families()`)
- [x] Registry: 标签批量查询可用 ✅ (v119 晚场 — `list_models_by_tags(tags, mode="any"|"all")` / `tag_index()` / CLI `--tags` + `--match` / `/api/registry?tags=`)
- [x] Registry: 旧元数据向后兼容 ✅ (v119 晚场 — `_normalize()` 读取时动态补齐 `version=1` + 派生 `family`，不重写旧 JSON；打/去标签只写回 `tags` 字段，旧文件形状不变)
- [x] P2: benchmarks harness 通过，报告写入 `benchmarks/reports/2026-10-25.md` ✅ (v119 晚场，acc 0.7900 / thr 0.7000)
- [x] P3: API 行为记录于 `spec/API.md`，`/api/health` 返回 200 ✅ (v119 晚场)

---

## DoD #3 实现说明（v119 晚场）

### 模型版本化

**family key** = `model_type|dataset_name|<sorted hyperparameters>`。
超参键按字典序排序，值用 `repr` 渲染 —— `{"C": 1.0}` 与 `{"C": 1}` 属不同 family（可能训练出不同结果）。

同一 family 内重新训练 → 版本递增 `v1 → v2 → v3 ...`；不同 family 各自从 `v1` 开始。

**向后兼容**：v12 之前注册的模型元数据**不被重写**。`RegistryManager._normalize()` 在读取时动态补齐：
- 缺失 `version` → `1`
- 缺失 `family` → 由 `model_type` / `dataset.name` / `hyperparameters` 派生

**写入不变量**：`tag_model()` / `untag_model()` 使用原始（未规范化）元数据，只写回 `tags` 字段 —— 给旧模型打标签**不会**把派生的 `version` / `family` 写入旧 JSON 文件。

模型 ID 格式不变（`YYYY-MM-DD_<6位hex>`），与 v12 之前完全一致。

### 标签批量查询

- `list_models_by_tags(tags, mode="any"|"all")` — `any` 为并集（至少命中一个），`all` 为交集（必须全部命中）；结果按 `created_at` 降序。
- `tag_index()` — `{tag: [model_id, ...]}`，每个桶内按 `created_at` 降序。
- 错误处理：空标签列表 → `ValueError("At least one tag is required for a batch tag query.")`；非法 mode → `ValueError("Invalid tag match mode '{mode}'. Expected 'any' or 'all'.")`。

### 触达面

| 层 | 新增能力 |
|----|----------|
| Registry | `family_key()` / `list_model_families()` / `get_model_versions()` / `get_latest_version()` / `list_models_by_tags()` / `tag_index()` / `_normalize()` |
| SDK (`ml_db`) | `list_models_by_tags()` / `tag_index()` / `list_model_families()` / `get_model_versions()` / `get_latest_version()` |
| CLI | `model list --tags A B --match any\|all`、`model versions <id>`、`model families`、`model list`/`inspect` 显示 VER 列 |
| HTTP | `GET /api/registry`（serverless `api/registry.py` + 本地 Flask `web/server.py` 同一契约） |
| Spec | `spec/API.md` 记录端点契约与版本化语义 |
