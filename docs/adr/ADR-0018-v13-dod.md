# ADR-0018 — v13 DoD 细化：Experiment Provenance & Reproducibility

**日期**: 2026-10-26
**状态**: 🟡 Proposed（DoD #1 实现完成，待 Accepted）
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

---

## 设计约束

- Provenance 只记录可复现性与诊断所需字段，不保存凭证或环境变量全集。
- Fingerprint 使用 canonical JSON + SHA-256；`captured_at` 与 `git.dirty` 不参与指纹。
- Registry 是事实源，SDK 与 CLI 仅调用同一核心逻辑，避免三端漂移。
- 旧 registry 零迁移：旧文件不重写。
- 不把通用部署托管或 AutoML 纳入范围，遵守 CHARTER Non-Goals。

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

## 下轮待办

1. 将 provenance 查询扩展到 HTTP API（如 `/api/provenance?id=...`）。
2. 为 provenance 增加可重放命令快照与依赖锁定摘要。
3. PR #60 合并后以 master 为 v13 基线，避免长期分叉。
