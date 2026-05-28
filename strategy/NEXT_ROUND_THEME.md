# NEXT_ROUND_THEME.md — ml-decision-boundary v22 (v6 进行中)

**更新时间：** 2026-05-28 21:47 CST
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

## ✅ 本轮完成（2026-05-28 晚场）

### PR 合并

- **PR#40**：v5→v6 升级 docs — 已合并
- **PR#41**：main.py 数据集去重 — 已合并
- **PR#42**：train_utils dedup + ADR-0009 — 待合并（冲突已解决）

### respx/httpx 冲突分析

**问题**：respx 0.23.1 依赖 httpx.BaseTransport，已在 httpx 0.28.1 中删除
**影响**：本地 pytest 无法收集测试（CI 不受影响，CI 只安装锁定依赖）
**修复方案**：升级 respx 到 0.24.0+，或在 conftest.py 中隔离

---

## 📊 当前 PR 状态

| PR | 标题 | 状态 |
|----|------|------|
| #42 | train_utils dedup + ADR-0009 | OPEN（rebase 解决冲突后待 merge） |

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest 无法本地运行 | P1（待修复） |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | 未处理 |

---

## 下轮待办

1. [ ] **PR#42 merge** — train_utils dedup + ADR-0009
2. [ ] **respx/httpx 修复**（ADR-0009 P1）— 方案：升级 respx 或 conftest 隔离
3. [ ] **API contract test 覆盖增强**（ADR-0009 P2）— TBD
4. [ ] **README/SPEC.md v6 同步**（ADR-0009 P3）— 等 PR#42 合并后做

---

**版本历史**：
- v22 (2026-05-28 21:47): 晚场 — PR#40/41 合并，PR#42 rebase 冲突解决
- v22 (2026-05-28 10:20): v6 启动，ADR-0009 完成，PR#42 open
- v21 (2026-05-27 22:15): main.py 去重完成，v5 全部完成，v6 启动