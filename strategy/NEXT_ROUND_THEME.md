# NEXT_ROUND_THEME.md — ml-decision-boundary v22 (v6 进行中)

**更新时间：** 2026-05-28 10:20 CST
**版本：** v22 (v6 第一天，进行中)
**维护人：** 太子

---

## 📋 当前阶段状态

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| v0 Foundation | ✅ | 2026-04-26 |
| v1 Testing & Harness | ✅ | 2026-04-29 |
| v2 Model & Data Expansion | ✅ | 2026-05-06 |
| v3 Platform | ✅ | 2026-05-19 |
| v4 Reproducibility & Robustness | ✅ | 2026-05-24 |
| v5 Automation & Documentation | ✅ | 2026-05-27 |
| v6 Stability & Extensibility | 进行中 | 2026-05-28（启动） |

---

## v6 DoD（来自 ADR-0009）

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | test_api_contract.py respx/httpx 冲突修复 | pytest 可运行（本地 env issue，根因已定位） | P1（待修复） |
| 2 | core/train_utils.py build_model 重复定义清理 | 文件无重复 def，从 192→140 行 | ✅ 已完成（PR#42） |
| 3 | API contract test 覆盖增强 | TBD | P2 |
| 4 | Release 自动化（GitHub Release） | TBD | P2 |
| 5 | README/SPEC.md 同步 v6 | 同步 v5 完成 + v6 阶段定义 | P3 |

---

## ✅ 本轮完成（2026-05-28 早场）

### PR#42：core/train_utils.py 重复定义 + ADR-0009

**本轮 commit**：
- `core/train_utils.py`：删除 lazy `__import__` factory + direct `build_model` 重复定义，统一为直接 sklearn import 顶层（-52 行）
- `docs/adr/ADR-0009-v6-dod.md`：v6 DoD 细化完成（3 个 P1/P2 候选）
- `strategy/runs/2026-05-28-1014.md`：本轮 run log（深度发现 + 根因分析）
- `CHANGELOG.md`：Unreleased 已更新

---

## 📊 CI 状态

| PR | 标题 | 状态 | 说明 |
|----|------|------|------|
| #40 | v5→v6 升级 docs | OPEN | 等待 review |
| #41 | main.py 数据集去重 | OPEN | 等待 review |
| #42 | train_utils dedup + ADR-0009 | OPEN | 刚 push，CI 运行中 |

---

## 本地环境问题：respx/httpx 冲突

**现象**：本地 pytest 无法收集（respx 0.23.1 + httpx 0.28.1 不兼容）
**CI 不受影响**：requirements.lock 无 respx/httpx，CI 只安装锁定依赖
**根因**：respx 0.23.1 依赖 httpx.BaseTransport，已在 httpx 0.28.1 删除
**修复方案**：pip install respx==0.24.0+（或 conftest.py 隔离）

---

## 下轮待办

1. [ ] **PR#40 merge**（等待 review）— v5→v6 升级 docs
2. [ ] **PR#41 merge**（等待 review）— main.py 数据集去重
3. [ ] **PR#42 CI 状态确认**（已推送）
4. [ ] **respx/httpx 修复**（ADR-0009 P1）— 方案：升级 respx 或 conftest 隔离
5. [ ] **README/SPEC.md v6 同步**（ADR-0009 P3）— 等 PR#40 合并后做

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest 无法本地运行 | P1（待修复） |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理（本 PR） |
| C3 | api/health.py 缺 docstring | P3 | 未处理 |

---

**版本历史**：
- v22 (2026-05-28 10:20): v6 启动，ADR-0009 完成，PR#42 open
- v21 (2026-05-27 22:15): main.py 去重完成，v5 全部完成，v6 启动
