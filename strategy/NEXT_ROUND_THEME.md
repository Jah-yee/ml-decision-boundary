# NEXT_ROUND_THEME.md — ml-decision-boundary v17 (v5 work)

**更新时间：** 2026-05-25 09:50 CST
**版本：** v17 (v5 启动：阶段升级 + PR#37 合并)
**维护人：** 太子

---

## 📋 当前阶段状态

### v1-v4 完成摘要

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| v0 Foundation | ✅ | 2026-04-26 |
| v1 Testing & Harness | ✅ | 2026-04-29 |
| v2 Model & Data Expansion | ✅ | 2026-05-06 |
| v3 Platform | ✅ | 2026-05-19 |
| v4 Reproducibility & Robustness | ✅ | 2026-05-24 |

---

## v4 DoD 最终完成确认

**全部 4 项已在 2026-05-24 完成（PR#37）**

| # | Item | 证据 |
|---|------|------|
| 1 | REPRODUCE.md v4 update | commit 59358c8, 8777 bytes |
| 2 | Tree depth CI integration | depth-sweep job in ci.yml |
| 3 | Hyperparam sweep regression detection | PR#37: stored vs inline baseline split fix |
| 4 | Boundary case test coverage | tests/test_boundary_cases.py, 116 tests |

**CI 验证通过**: quality-gates ✅ | benchmark ✅ | depth-sweep ✅ | hyperparam-sweep ✅ (regressions=0)

---

## ✅ 本轮完成（2026-05-25 上午场）

### 重大里程碑：v4 → v5 阶段升级

**PR#37 合并**：fix/hyperparam-baseline-self-comparison → master
- 2026-05-25 squash-merged to master (commit a76c79e)
- 包含：hyperparam_baseline.json 刷新、run.py 修复、test_boundary_cases.py (116 tests)

**ADR-0006 创建**：v4→v5 阶段升级判定，正式记录 v4 完成

**phases.md 更新**：v4 完成标记，v5 启动

### P0/P1 验证
- P0 compileall: ✅ 通过
- P1 pytest (26 tests subset): ✅ 26 passed in 0.86s
- P1 pytest boundary_cases: ✅ 116 passed in 6.83s

---

## 🎯 v5 主题方向（Automation & Documentation）

**候选方向（待第一轮 cron 细化）**：

1. **自动化发行/发布流程** — GitHub Release 自动化、版本号管理、CHANGELOG 生成
2. **依赖安全审核** — pip-audit 集成、漏洞告警机制
3. **文档完整性自动化检查** — README/SPEC.md 同步验证
4. **README/SPEC.md 一致性** — 确保文档与代码实现同步

### v5 Non-Goals（明确不做）

- 多语言 SDK
- AutoML / 超参搜索平台
- 模型生产部署托管

---

## 下轮待办

1. [ ] v5 DoD 细化（第一轮 cron 确定）
2. [ ] ADR-0006 创建 ✅ (2026-05-25)
3. [ ] phases.md 更新 ✅ (2026-05-25)
4. [ ] PR#35 (web traceback 修复) 合并冲突解决