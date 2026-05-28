# NEXT_ROUND_THEME.md — ml-decision-boundary v21 (v5 完成, v6 进行中)

**更新时间：** 2026-05-27 22:15 CST
**版本：** v21 (v5 全部完成, v6 进行中)
**维护人：** 太子

---

## 📋 当前阶段状态

### v1-v5 完成摘要

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| v0 Foundation | ✅ | 2026-04-26 |
| v1 Testing & Harness | ✅ | 2026-04-29 |
| v2 Model & Data Expansion | ✅ | 2026-05-06 |
| v3 Platform | ✅ | 2026-05-19 |
| v4 Reproducibility & Robustness | ✅ | 2026-05-24 |
| v5 Automation & Documentation | ✅ | 2026-05-27 |
| v6 Stability & Extensibility | 进行中 | 2026-05-27 |

---

## v5 DoD（来自 ADR-0007）

### v5 DoD 候选项目（3 项，已全部完成 ✅）

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | CHANGELOG 自动化生成 | `scripts/generate_changelog.py` 成功运行 | ✅ 完成（PR#38）|
| 2 | 依赖安全审核 CI | pip-audit 集成到 CI，security-audit job 通过 | ✅ 完成（PR#39）|
| 3 | README/SPEC.md 一致性 CI | `scripts/check_readme_consistency.py` 集成到 CI quality-checks | ✅ 完成（PR#39）|

**排除项目**：GitHub Release 自动化（推迟到 v6）

---

## ✅ 本轮完成（2026-05-27 晚场）

### main.py 数据集去重 + PR#41 创建

**PR#41**：refactor: delegate dataset generation to core/datasets.py
- 删除 5 个本地函数：`make_circles`, `make_moons`, `make_blobs`, `make_xor`, `make_s_curve`（-51 行）
- `generate_dataset()` 改用 `core.datasets.DATASET_GENERATORS` dispatch
- 新增 re-export 块，保持 tests/ 和 benchmarks/ 向后兼容
- CI 全部 job 通过（quality-gates, benchmark, depth-sweep, hyperparam-sweep, security-audit, quality-checks）

---

## 🎯 v5 Non-Goals（明确不做）

- 多语言 SDK
- AutoML / 超参搜索平台
- 模型生产部署托管

---

## 下轮待办

1. [ ] **PR#41 merge**（等待 CI + review）— main.py 数据集去重
2. [ ] **PR#40 merge**（等待 review）— v5→v6 升级 docs
3. [ ] **v6 DoD 细化**（来源：ADR-0008）— 候选：测试覆盖增强 / API contract test / Release 自动化
4. [ ] **respx/httpx 依赖冲突修复**（来源：本轮发现）— env issue, not code issue
5. [ ] **docstring 补充**（来源：本轮扫描，中优先级）— api/train.py, scripts/*.py 等 13 个文件
6. [ ] **清理未跟踪文件** strategy/runs/2026-05-22-1004.md

---

## 📊 CI 状态

- master: 所有 job 通过
- refactor/deduplicate-main-py (PR#41): 所有 job 通过 ✅
- daily/v5-to-v6-upgrade (PR#40): OPEN，等待 review

---

## 已知技术债务

| # | 问题 | 影响 | 优先级 |
|---|------|------|--------|
| 1 | respx/httpx 依赖冲突 | test_api_contract.py 等无法运行 | P2 |
| 2 | 13 个核心文件缺少 docstring | API 文档可读性 | P2 |
| 3 | core/train_utils.py 有重复的 build_model 定义（lazy + direct import） | 死代码 | P3 |

---

**版本历史**：
- v21 (2026-05-27 22:15): main.py 数据集去重完成，PR#41 创建，技术债务清单
- v20 (2026-05-27 10:21): v5 全部完成，v6 启动，ADR-0008 创建，PR#40 open
- v19 (2026-05-26 09:50): v5 DoD 全部 3 项完成，PR#39 合并
- v18 (2026-05-25 21:50): v5 DoD 细化完成，ADR-0007 创建，PR#38 创建
- v17 (2026-05-25 09:50): v5 阶段启动
