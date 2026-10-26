# ADR-0018 — v13 DoD 细化：Experiment Provenance & Reproducibility

**日期**: 2026-10-26
**状态**: 🟡 Proposed（DoD #1 实现中）
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
| 1 | Provenance capture | 注册模型时记录 seed / dataset params / resolved hyperparameters / environment / git commit / canonical fingerprint | P1 | 🟡 实现中 |
| 2 | Provenance compare | SDK + CLI 支持查看 provenance 与比较两个模型的来源差异 | P1 | 🟡 实现中 |
| 3 | Backward compatibility | v13 前模型无需迁移；读取时返回空 provenance，不重写旧 JSON | P1 | 🟡 实现中 |
| 4 | Regression verification | 新增专项测试，完整 P0/P1/P2/P3 验收，CI 全绿 | P0 | ⏳ 待验收 |

---

## 设计约束

- Provenance 只记录可复现性与诊断所需字段，不保存凭证或环境变量全集。
- Fingerprint 使用 canonical JSON + SHA-256；`captured_at` 与 `git.dirty` 不参与指纹。
- Registry 是事实源，SDK 与 CLI 仅调用同一核心逻辑，避免三端漂移。
- 旧 registry 零迁移：旧文件不重写。
- 不把通用部署托管或 AutoML 纳入范围，遵守 CHARTER Non-Goals。

---

## 验收标准

- [ ] Registry 新模型包含完整 provenance JSON
- [ ] `MLDB.get_provenance()` / `MLDB.compare_provenance()` 可用
- [ ] CLI `model provenance <id>` / `model diff <id1> <id2>` 可用
- [ ] 旧模型返回空 provenance 且原 JSON 字节不变
- [ ] Fingerprint 对 volatile 字段稳定，对 seed/参数/环境/git 变化敏感
- [ ] P0 compileall + import smoke 通过
- [ ] P1 pytest 全绿
- [ ] P2 benchmark quick 通过
- [ ] P3 API/health 契约保持通过

---

## 下轮待办

1. 将 provenance 查询扩展到 HTTP API（如 `/api/provenance?id=...`）。
2. 为 provenance 增加可重放命令快照与依赖锁定摘要。
3. PR #60 合并后以 master 为 v13 基线，避免长期分叉。
