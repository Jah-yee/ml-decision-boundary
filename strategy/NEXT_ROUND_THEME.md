# NEXT_ROUND_THEME.md — ml-decision-boundary v18 (v5 work)

**更新时间：** 2026-05-25 21:50 CST
**版本：** v18 (v5 DoD 细化完成 + PR#38)
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
| v5 Automation & Documentation | 进行中 | 2026-05-25 |

---

## v5 DoD（来自 ADR-0007）

### v5 DoD 候选项目（3 项，已确定）

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | CHANGELOG 自动化生成 | `scripts/generate_changelog.py` 成功运行 | ✅ 完成（PR#38）|
| 2 | 依赖安全审核 CI | pip-audit 集成到 CI，security-audit job 通过 | 待做 |
| 3 | README/SPEC.md 一致性 CI | `scripts/check_readme_consistency.py` 集成到 CI quality-gates | 待做 |

**排除项目**：GitHub Release 自动化（推迟到 v5 后期）

---

## ✅ 本轮完成（2026-05-25 晚场）

### v5 DoD 细化 + CHANGELOG 自动化脚本

**PR#35 已关闭**：fix/web-error-traceback-leak 的内容（commit 06f663b）已通过 PR#37 进入 master，PR 关闭

**ADR-0007 创建**：v5 DoD 细化提案（3 项：CHANGELOG 自动化、依赖安全审核、README 一致性检查）

**PR#38**：docs: v5 DoD 细化 + CHANGELOG 自动化脚本 init
- `CONTRIBUTING.md` P1 测试数更新（100→216）
- `REPRODUCE.md` verified date 更新为 2026-05-25
- `scripts/generate_changelog.py` 创建（203 行 conventional commit parser）
- `docs/adr/ADR-0007-v5-dod.md` 创建
- CHANGELOG Unreleased 更新

### P0/P1 验证
- P0 compileall: ✅ 通过
- P1 pytest (test_main + test_api_contract): ✅ 28 passed in 1.13s
- P1 pytest boundary_cases: ✅ 116 passed in 29.39s

---

## 🎯 v5 主题方向（Automation & Documentation）

### 主题确认
1. **CHANGELOG 自动化** — ✅ `scripts/generate_changelog.py` 完成
2. **依赖安全审核** — pip-audit CI（待实现）
3. **文档一致性** — README/SPEC.md CI（待实现）

### v5 Non-Goals（明确不做）
- 多语言 SDK
- AutoML / 超参搜索平台
- 模型生产部署托管

---

## 下轮待办

1. [ ] 实现 ADR-0007 DoD 项目 2：pip-audit 安全审核 CI
2. [ ] 实现 ADR-0007 DoD 项目 3：README/SPEC.md 一致性检查
3. [ ] PR#38 合并（CI 通过后）

---

## 📊 CI 状态

- PR#38 (daily/v5-init-automation-docs): quality-gates + benchmark jobs in progress

---

**版本历史**：
- v18 (2026-05-25 21:50): v5 DoD 细化完成，ADR-0007 创建，PR#38 创建
- v17 (2026-05-25 09:50): v5 阶段启动