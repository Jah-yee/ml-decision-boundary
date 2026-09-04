# phases.md - 阶段定义

**版本**: v0.3 (Created 2026-04-26, Updated 2026-06-06)
**更新**: v7 阶段完成 + v8 阶段添加 (2026-06-06)

---

## v0 - Foundation (已完成 ✅)

**入口条件**: 仓库可 clone、可 install requirements、可 `python3 main.py` 成功运行并产生 output/ 下的可视化文件。

**出口条件**:
- P0 通过(compileall + import smoke)
- P1: 有测试基础设施(至少 conftest + 1 个测试用例)
- P2: `python3 main.py` 可执行,产生 JSON + PNG
- P3: API health 返回 200,Web 可本地启动

**本阶段 DoD**:
- [x] README 说明清晰,可 clone → run
- [x] main.py 可独立运行
- [x] 有 requirements.txt
- [x] 有 vercel.json
- [x] 有 output/ 目录
- [x] P1: 测试基础设施(pytest>=7.0.0)
- [x] P1: 35 tests passed
- [x] P2: harness 可重复运行(固定 seed + JSON report schema)
- [x] P3: 集成测试(health check)

**v0 已完成 ✅ | v1 进行中**

---

## v1 - Testing & Harness (已完成 ✅)

---

## v2 - Model & Data Expansion (已完成 ✅)

**入口条件**: v1 DoD 全部完成 ✅

**本阶段 DoD**:
- [x] SPEC.md 拆分 ✅ (PR#19, 2026-05-03)
- [x] CLI 帮助文本改进 ✅ (PR#20, 2026-05-05)
- [x] ADR-0002: Phase v1 → v2 升级判定 ✅ (2026-05-02)
- [x] GitHub Actions CI 配置 ✅ (2026-05-06)
- [x] CONTRIBUTING.md 完善 ✅ (PR#20, 2026-05-06)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅**

### v2 附加目标
- 扩展模型族(新增模型类型或超参数配置)
- 新数据集支持(更多合成数据场景)
- 模型超参数调优实验体系
- benchmark 报告自动化(HTML schema)

---

## v3 - Platform (已完成 ✅)

**入口条件**: v2 DoD 全部完成 ✅

**本阶段 DoD**:
- [x] ADR-0003: Phase v2 → v3 升级判定 ✅ (2026-05-08)
- [x] 新模型支持或超参数调优实验体系 ✅ - 超参调优实验体系基础设施 (PR#34, 2026-05-17)
- [x] 新数据集支持 ✅ - s_curve 数据集 (PR#31, 2026-05-15)
- [x] CLI/Web/API 平台化 ✅ - core/ 模块提取 (PR#36, 2026-05-19)
- [x] ADR-0004: v3 平台化决策 ✅ (2026-05-19)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅**

---

## v4 - Reproducibility & Robustness (已完成 ✅)

**入口条件**: v3 DoD 全部完成 ✅ + ADR-0004 Accepted + ADR-0005 Accepted

**本阶段 DoD**:
- [x] ADR-0005: Phase v3 → v4 升级判定 ✅ (2026-05-19)
- [x] REPRODUCE.md v4 update ✅ (2026-05-20)
- [x] Tree depth sensitivity matrix CI integration ✅ (2026-05-20)
- [x] Hyperparam sweep regression detection automation ✅ (PR#37, 2026-05-24)
- [x] Platform boundary case test coverage ✅ (PR#37, 2026-05-24)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅**

---

## v5 - Automation & Documentation (已完成 ✅)

**入口条件**: v3 DoD 全部完成 ✅ + ADR-0004 Accepted + ADR-0005 Accepted

**本阶段 DoD**:
- [x] ADR-0006: Phase v4 → v5 升级判定 ✅ (2026-05-25)
- [x] CHANGELOG 自动化生成 ✅ (PR#38, 2026-05-25)
- [x] 依赖安全审核 CI(pip-audit 集成)✅ (PR#39, 2026-05-26)
- [x] README/SPEC.md 一致性 CI ✅ (PR#39, 2026-05-26)
- [x] ADR-0007: v5 DoD 细化 → Accepted ✅ (2026-05-26)
- [x] ADR-0008: Phase v5 → v6 升级判定 ✅ (2026-05-27)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅**

---

## v7 — Extensibility, Edge Cases & UX (已完成 ✅)

**入口条件**: v6 DoD 全部完成 ✅ + ADR-0009 Accepted + ADR-0010 Proposed (2026-06-01)

**本阶段 DoD**（ADR-0011）：
- [x] ADR-0011: v7 DoD 细化 ✅ (2026-06-01)
- [x] 自定义模型插件接口 ✅ (PR#50, 2026-06-06)
- [x] 数据集边界验证 ✅ (PR#51, 2026-06-06)
- [x] 错误信息改进 ✅ (PR#52, 2026-06-06)
- [x] C4: pytest 超时修复 ✅ (PR#53, 2026-06-06)
- [x] ADR-0011 Accepted ✅ (2026-06-06)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅ | v6 已完成 ✅ | v7 已完成 ✅**

---

## v8 — Model Registry & Lifecycle (已完成 ✅)

**入口条件**: v7 DoD 全部完成 ✅ + ADR-0011 Accepted + ADR-0012 Proposed (2026-06-06)

**本阶段 DoD**（ADR-0013）：
- [x] ADR-0013: v8 DoD 细化 ✅ (2026-06-07)
- [x] Model Registry 核心（训练结果自动注册，元数据持久化）✅ (PR#55, v34 bugfix)
- [x] 模型序列化（save/load 接口）✅ (PR#55, v34 bugfix)
- [x] CLI 模型管理命令 ✅ (PR#55)
- [x] Benchmark Registry CLI（`ml-db benchmark list`/`inspect`/`regressions`）✅ (本轮)
- [x] ADR-0013 Accepted ✅ (2026-07-04)
- [x] v8 DoD #1-4 全部完成 ✅ (PR#55 merged 2026-07-04)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅ | v6 已完成 ✅ | v7 已完成 ✅ | v8 已完成 ✅ 🎉**

---

## v9 — Documentation, Examples & Registry UX (已完成 ✅)

**入口条件**: v8 DoD 全部完成 ✅ + ADR-0013 Accepted (2026-07-04) + ADR-0014 Proposed (2026-07-05)

**本阶段 DoD**（ADR-0014 — ✅ Accepted 2026-07-08）：
- [x] ADR-0014: v9 DoD 细化 ✅ (2026-07-08 Accept，v9 DoD #1-4 全部完成)
- [x] 示例脚本集 (`examples/01~05_*.py`) — 5 个独立可运行脚本 ✅ (v50 晚场)
- [x] Cookbook 文档 (`docs/cookbook.md`) — 6章节，606行 ✅ (v51 早场)
- [x] Registry CLI 增强 (`compare` / `tag` / `list --tag`) ✅ (v51 晚场)
- [x] README 改进 (Quick Start + Architecture + 功能徽章) ✅ (v52 早场)
- [x] ADR-0014 Accepted 后同步至 phases.md + NEXT_ROUND_THEME ✅ (v52 晚场)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅ | v6 已完成 ✅ | v7 已完成 ✅ | v8 已完成 ✅ | v9 已完成 ✅ 🎉**

---

## v10 — API Enhancement & Interactive Web UI (已完成 ✅)

**入口条件**: v9 DoD 全部完成 ✅ + ADR-0014 Accepted (2026-07-08) + ADR-0015 Draft (2026-07-09)

**本阶段 DoD**（ADR-0015 — ✅ Accepted 2026-07-10）：
- [x] ADR-0015: v10 DoD 细化 ✅ (2026-07-10 Accepted)
- [x] API Model Detail Endpoint — `GET /api/models/<name>` 返回模型元数据 ✅ (v53 晚场)
- [x] API Dataset Listing Endpoint — `GET /api/datasets` 返回可用数据集列表 ✅ (v53 晚场)
- [x] Web UI: Model Comparison View — 多模型并排对比边界视图 ✅ (v54 早场)
- [x] Web UI: Parameter Presets — SVM/RF/KNN 快速预设按钮 ✅ (v54 早场)
- [x] ADR-0015 Accepted ✅ (2026-07-10)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅ | v6 已完成 ✅ | v7 已完成 ✅ | v8 已完成 ✅ | v9 已完成 ✅ | v10 已完成 ✅ 🎉**

---

## v11 — Multi-Dataset Expansion & Experiment History (进行中 🟡)

**入口条件**: v10 DoD 全部完成 ✅ + ADR-0015 Accepted (2026-07-10) + ADR-0016 Draft (2026-07-10)

**本阶段 DoD**（ADR-0016 — 🟡 Draft）：
- [x] ADR-0016: v11 DoD 细化 ✅ (v55 晚场 Draft)
- [x] Multi-Dataset Support — 新增 swiss_roll + make_classification 变体 ✅ (v56 早场)
- [x] Batch Prediction API — `POST /api/predict/batch` ✅ (v56 晚场)
- [x] Experiment History UI — Web UI 历史实验面板 + output/experiments.jsonl ✅ (v57 早场)
- [ ] ADR-0016 Accepted — DoD #1-3 全部完成后 Accept 🟡

**v0 已完成 ✅ | v1 已完成 ✅ | v2 已完成 ✅ | v3 已完成 ✅ | v4 已完成 ✅ | v5 已完成 ✅ | v6 已完成 ✅ | v7 已完成 ✅ | v8 已完成 ✅ | v9 已完成 ✅ | v10 已完成 ✅ | v11 进行中 🟡**

---

## 阶段升级判定规则

- 每个 phase 的 P0 必须通过才能进入下一 phase
- phase 升级需要创建 `docs/adr/NNNN-phase-N-to-N+1.md`
- phase 之间禁止跳跃(必须顺序通过)