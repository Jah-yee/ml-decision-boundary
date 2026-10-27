# ADR-0018 — v13 DoD 细化：Experiment Provenance & Reproducibility

**日期**: 2026-10-26（2026-10-27 追加 DoD #8 / #9）
**状态**: 🟡 Proposed（DoD #1–#3 + #5–#9 实现完成，待 Accepted）
**维护人**: 太子

---

## 背景

v12 Python API & SDK Foundation 的 DoD #1-#4 已全部完成，ADR-0017 已 Accepted，PR #60 已交付且 CI 6/6 SUCCESS。

CHARTER 的工程使命要求“每一次训练都可追溯、可回归测试、可集成到部署流水线”。v12 Registry 已记录模型结果、数据集 hash、超参数与版本族，但缺少训练条件本身：随机种子、完整数据集参数、运行环境、Git commit。v13 聚焦实验 provenance，让两个模型是否“同条件产生”可以被机器验证。

---

## v13 主题

**Experiment Provenance & Reproducibility**

---

## v13 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | Provenance capture | 注册模型时记录 seed / dataset params / resolved hyperparameters / environment / git commit / canonical fingerprint | P1 | ✅ 完成 (855f045) |
| 2 | Provenance compare | SDK + CLI 支持查看 provenance 与比较两个模型的来源差异 | P1 | ✅ 完成 (855f045) |
| 3 | Backward compatibility | v13 前模型无需迁移；读取时返回空 provenance，不重写旧 JSON | P1 | ✅ 完成 (855f045) |
| 4 | Regression verification | 新增专项测试，完整 P0/P1/P2/P3 验收，CI 全绿 | P0 | ⏳ 待 CI |
| 5 | Replay recipe | provenance 附带可执行重放方案（SDK 精确片段 + CLI 命令 + 依赖锁定摘要） | P1 | ✅ 完成 (5e7f843) |
| 6 | HTTP provenance API | `GET /api/provenance` 暴露 provenance / diff / replay | P1 | ✅ 完成 (5e7f843) |
| 7 | Honest replay | CLI 重放命令仅在可精确复现时标记 exact，否则警告并引导使用 SDK | P1 | ✅ 完成 (5e7f843) |
| 8 | Coverage dashboard | 覆盖率看板：哪些模型缺 provenance、哪些不可重放、阻塞原因分组 | P1 | ✅ 完成 (29089b1) |
| 9 | Replay execution | CLI `model replay --run <id>` 实际重跑并输出复现报告（run-equivalent 判定） | P1 | ✅ 完成 (29089b1) |

---

## 设计约束

- Provenance 只记录可复现性与诊断所需字段，不保存凭证或环境变量全集。
- Fingerprint 使用 canonical JSON + SHA-256；`captured_at` 与 `git.dirty` 不参与指纹。
- Registry 是事实源，SDK 与 CLI 仅调用同一核心逻辑，避免三端漂移。
- 旧 registry 零迁移：旧文件不重写。
- 不把通用部署托管或 AutoML 纳入范围，遵守 CHARTER Non-Goals。

### DoD #2 补充约束（重放诚实性）

- **重放命令必须诚实**：`main.py --params` 会把 `KEY=VALUE` 强制转为 int/float/bool，其余一律保留为**字符串**。因此 `hidden_layer_sizes=(50,)` 会被当成字符串 `"(50,)"` 传给 sklearn，**静默训练出一个不同的模型**。
- 重放方案提供两条路径：
  - `sdk` — 始终精确的 Python 片段（`MLDB.train(...)`，含 seed / test_size / 原始类型超参）。
  - `cli` — 便捷命令，**仅当**所有超参都能无损往返且 `test_size` 为默认值、`model_type` 属于 CLI 词表时才标记 `exact: true`；否则 `exact: false` + `warnings` 列表。
- 禁止在 CLI 路径声称“精确”而实际会产出不同模型。
- 依赖摘要基于 `requirements.lock` 的 SHA-256；文件缺失时降级为 `unknown` 而非报错。
- 重放判定区分两层：`run_equivalent`（seed / dataset / model_type / hyperparameters 相同，即“训练结果等价”）与 `fingerprint_match`（含 environment / git commit 的完整指纹相同）。前者才是复现性的正确判据。

---

## 验收标准

- [x] Registry 新模型包含完整 provenance JSON
- [x] `MLDB.get_provenance()` / `MLDB.compare_provenance()` 可用
- [x] CLI `model provenance <id>` / `model diff <id1> <id2>` 可用
- [x] 旧模型返回空 provenance 且原 JSON 字节不变
- [x] Fingerprint 对 volatile 字段稳定，对 seed/参数/环境/git 变化敏感
- [x] P0 compileall + import smoke 通过
- [x] P1 pytest 全绿
- [x] P2 benchmark quick 通过（accuracy 0.79 ≥ 0.70）
- [x] P3 API/health 契约保持通过（`/api/health` 200；`/api/registry` 五种查询契约实测通过）

---

## 实现要点

- `core/provenance.py`：唯一实现源。`build_provenance()` 组装记录，`compute_fingerprint()` 用 canonical JSON + SHA-256（前 16 hex）计算指纹。
- 指纹覆盖：seed / dataset / hyperparameters / 环境版本(python, numpy, scikit_learn, joblib) / git commit。
- 指纹不覆盖：`captured_at`、`git.dirty`、`git.branch`、`environment.platform` — 这些是采集上下文而非复现条件，避免“指纹相同但记录不同”的语义冲突。
- `provenance_diff()` 返回结构化差异（`field`/`left`/`right`），不把 JSON 当字符串比较。
- Registry 为事实源：`save_model(provenance=...)`、`get_provenance()`、`compare_provenance()`；旧模型读回空 `{}` 且不重写原 JSON。
- SDK：`MLDB.get_provenance()` / `MLDB.compare_provenance()`，缺失模型抛 `ModelNotFoundError`。
- CLI：`python3 main.py model provenance <id>`、`python3 main.py model diff <id1> <id2>`。
- 附带修复：`tests/test_benchmarks_smoke.py` full-suite 子进程超时 120s → 300s（实测该套件在本机稳定超过 120s，属测试预算问题，非产品缺陷）。

## DoD #2 实现要点

- `core/provenance.py` 新增：
  - `build_replay_command(record)` — 生成 CLI 命令并判定 `exact`；`cli_params_roundtrip_safe()` 负责识别 CLI 无法无损表示的值（tuple / list / dict / None）。
  - `build_replay_plan(record)` — 组装完整方案：`sdk` / `cli` / `dependencies` / `expected`（含原 fingerprint）。
  - `dependency_digest(repo_root)` — 对 `requirements.lock` 求 SHA-256（前 16 hex）+ 统计 pinned 包数；文件缺失时返回 `available: false`。
- `core/registry.py`：注册时把 replay 方案**冻结**进 provenance（`provenance["replay"]`）；`get_replay_plan()` 对 DoD #2 之前注册的模型按需推导，对 v13 之前的模型返回 `available: false` 而非报错，且不重写旧 JSON。
- `ml_db/client.py`：`MLDB.replay_plan()` / `MLDB.replay()`。`replay()` 使用**记录中的 seed**（而非客户端当前 seed，调用后恢复原值），默认 `register=False` 避免污染 registry。
- `api/provenance.py` + `web/server.py`：`GET /api/provenance`，`id`（必填）/ `compare` / `replay` 三种模式；400（缺 id）/ 404（模型不存在）/ 500（其它）三档状态码与 serverless 一致。
- `main.py`：`python3 main.py model replay <id>` 打印 CLI 命令（带 exact 标注与警告）+ 精确 SDK 片段。
- `tests/test_replay.py`：31 个新测试，含对真实 `main.parse_params` 行为的回归锁定（防止未来修改 CLI 解析器后“重放诚实性”静默失效）。

## DoD #3 实现要点（覆盖率看板 + 重放执行）

- `core/coverage.py`（新建，唯一实现源，只读）：
  - `classify_model(model, replay_plan=None)` — 将单个注册模型归类为 4 种状态之一：
    `replayable_exact` / `replayable_sdk` / `provenance_only` / `no_provenance`。
  - `provenance_coverage(models, replay_plans=None)` — 逐模型分类。
  - `coverage_summary(models, replay_plans=None)` — 聚合计数与百分比（`coverage_pct` / `replayable_pct` / `cli_exact_pct`）。
  - `replayability_report(models, replay_plans=None)` — 按“阻塞原因”分组，输出 `{reason, count, models}`，最常见原因在前。
  - `cli_replay_check(model)` — 比对冻结的 replay 快照与当前推导结果，检测快照漂移。
- **分类正确性的关键点**：DoD #1 时期注册的模型有 provenance 但没有冻结的 replay 快照，其方案可**按需推导**。若仅看快照，这些模型会被误判为 `provenance_only`。因此 `RegistryManager.provenance_coverage()` 先为所有带 provenance 的模型解析一次 `get_replay_plan()`（结果缓存于内存，不写回磁盘），使覆盖率与 registry 自身的判定一致。
- **只读保证**：审计全程不重写任何旧 JSON。`tests/test_coverage.py` 以字节比对锁定这一点。
- `core/registry.py`：`RegistryManager.provenance_coverage()` 返回 `{summary, report, models}`。
- `ml_db/client.py`：`MLDB.coverage()` / `MLDB.coverage_summary()`。
- `main.py`：
  - `python3 main.py model coverage` — 覆盖率看板（总数、覆盖率、精确率、状态分布、阻塞原因 Top-N）。
  - `python3 main.py model replay <id> --run` — **实际重跑**该实验，输出 `reproduced` / `fingerprint_match` / accuracy 差异 / run-level 差异；未复现时以退出码 2 结束。
- `api/provenance.py` + `web/server.py`：`GET /api/provenance?coverage=1`（无需 `id`）返回全量审计结果；两套实现镜像同一契约。
- `tests/test_coverage.py`：28 个新测试，覆盖 4 类状态分类、汇总百分比、阻塞原因分组、快照漂移检测、只读保证、CLI/HTTP 契约。

### 实测结果（真实 registry，20713 个模型）

| 指标 | 数值 |
|------|------|
| 模型总数 | 20713 |
| 带 provenance | 1109（5.35%） |
| 可重放 | 1109（5.35%，其中 1032 CLI 精确、77 需走 SDK） |
| 无 provenance（v13 前注册） | 19604 |
| 审计耗时 | ≈1.1s |

> 结论：v13 前注册的 19604 个模型永远不可重放（历史事实，不可追补）；覆盖率提升的唯一路径是**新注册模型默认携带 provenance**（已由 `save_model` 默认行为保证）。

## 下轮待办

1. PR #60 / #61 合并后以 master 为 v13 基线，避免长期分叉。
2. 将重放方案导出为独立文档（如 `docs/REPRODUCE.md`），便于离线审计。
3. Registry 体积治理（当前 4.0G / 20713 模型），避免磁盘占用无上限增长。
