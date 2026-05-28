# ADR-0008 — Phase v5 → v6 升级判定

**日期**: 2026-05-27
**状态**: Accepted
**决策者**: 太子

---

## 背景

v5（Automation & Documentation）阶段已完成全部 3 项 DoD 项目：

| # | DoD 项目 | 状态 |
|---|---------|------|
| 1 | CHANGELOG 自动化生成 | ✅ 完成（PR#38） |
| 2 | 依赖安全审核 CI（pip-audit） | ✅ 完成（PR#39） |
| 3 | README/SPEC.md 一致性 CI | ✅ 完成（PR#39） |

同时 ADR-0007 已于 2026-05-26 09:59 更新为 Accepted 状态，DEPENDENCY_POLICY.md 已包含 pip-audit 集成说明。

v5 的所有计划目标均已完成，项目具备进入 v6 的条件。

---

## v5 阶段总结

### 完成项
- CHANGELOG 自动化（`scripts/generate_changelog.py`）
- pip-audit CI 集成（`security-audit` job）
- README 一致性 CI（`quality-checks` job）
- ADR-0007 → Accepted
- DEPENDENCY_POLICY.md pip-audit section
- CHANGELOG.md Unreleased 块已按本次更新

### 未完成项（已知）
- GitHub Release 自动化（从 v5 DoD 候选中排除，推迟到 v6）

---

## v6 方向提案

v6 主题：**平台稳定性与可扩展性**

v5 完成自动化基建后，项目需要：
1. 消化吸收 v5 引入的 CI 基础设施
2. 建立 v6 的质量基线（测试覆盖、benchmark 稳定性）
3. 清理技术债务

### v6 候选方向（待进一步细化）

| 方向 | 描述 | 优先级 |
|------|------|--------|
| 测试覆盖增强 | 补充 integration test 和 edge case test | P1 |
| API 稳定性保障 | 建立 API contract test，防止 breaking change | P1 |
| Benchmark 稳定性 | 解决 hyperparam baseline 的 false positive 回归 | P2 |
| 发布流程 | GitHub Release 自动化 | P2 |
| 文档完善 | v5/v6 更新统一到 README/SPEC | P2 |

### 判定
- v5 DoD 全部 3 项完成 ✅
- ADR-0007 已 Accepted ✅
- 本次更新已 commit 并 push ✅
- **结论**：满足 v5→v6 升级条件

---

## 决策

**升级 v5 → v6**，进入平台稳定性与可扩展性阶段。

下次 Owner cron 执行时以 v6 为主线，参照 phases.md v6 部分细化 DoD。

---

**版本历史**：
- v1 (2026-05-27): Initial — v5→v6 upgrade decision