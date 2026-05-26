# NEXT_ROUND_THEME.md — ml-decision-boundary v19 (v5 DoD 完成)

**更新时间：** 2026-05-26 09:50 CST
**版本：** v19 (v5 DoD 2/3 完成)
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
| v5 Automation & Documentation | 进行中 | 2026-05-26 |

---

## v5 DoD（来自 ADR-0007）

### v5 DoD 候选项目（3 项，已全部完成 ✅）

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | CHANGELOG 自动化生成 | `scripts/generate_changelog.py` 成功运行 | ✅ 完成（PR#38）|
| 2 | 依赖安全审核 CI | pip-audit 集成到 CI，security-audit job 通过 | ✅ 完成（PR#39）|
| 3 | README/SPEC.md 一致性 CI | `scripts/check_readme_consistency.py` 集成到 CI quality-checks | ✅ 完成（PR#39）|

**排除项目**：GitHub Release 自动化（推迟到 v5 后期）

---

## ✅ 本轮完成（2026-05-26 早场）

### v5 DoD 项目 2 & 3 完成 + PR#39 合并

**PR#39**：feat: ADR-0007 DoD items 2 & 3 — pip-audit CI + README consistency check
- `.github/workflows/ci.yml`：新增 `security-audit` + `quality-checks` jobs
- `scripts/check_readme_consistency.py`：README 与 main.py argparse 一致性检查（247 行）
- `scripts/security_audit.py`：pip-audit 本地 wrapper
- CI 全部 job 通过（quality-gates, benchmark, depth-sweep, hyperparam-sweep, security-audit, quality-checks）

**v5 DoD 全部 3 项完成**：
- [x] CHANGELOG 自动化（PR#38）
- [x] 依赖安全审核 CI（PR#39）
- [x] README/SPEC.md 一致性 CI（PR#39）

---

## 🎯 v5 Non-Goals（明确不做）

- 多语言 SDK
- AutoML / 超参搜索平台
- 模型生产部署托管

---

## 下轮待办

1. [ ] v5 阶段总结 + v6 阶段规划
2. [ ] ADR-0007 状态更新为 Accepted
3. [ ] DEPENDENCY_POLICY.md 反映 pip-audit 集成

---

## 📊 CI 状态

- master: 所有 job 通过（PR#39 merge 后触发）
- daily/v5-security-readme-ci: 已合并并删除

---

**版本历史**：
- v19 (2026-05-26 09:50): v5 DoD 全部 3 项完成，PR#39 合并
- v18 (2026-05-25 21:50): v5 DoD 细化完成，ADR-0007 创建，PR#38 创建
- v17 (2026-05-25 09:50): v5 阶段启动