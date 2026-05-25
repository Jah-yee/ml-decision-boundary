# ADR-0006 — Phase v4 → v5 升级判定

**日期**: 2026-05-25
**状态**: Accepted
**决策者**: Jah-yee <jydu_seven@outlook.com>

---

## 背景

v4 Reproducibility & Robustness 阶段的目标是确保平台化后的代码在各种边界条件下稳定运行，并提供完善的可复现性保证。

v4 DoD 已在 2026-05-22 全部完成（PR#37），CI 所有 jobs 均通过。

---

## v4 DoD 完成状态

| DoD 项 | 状态 | 关联 PR/Commit |
|--------|------|----------------|
| REPRODUCE.md v4 update | ✅ | commit 59358c8 (2026-05-20) |
| Tree depth sensitivity matrix CI integration | ✅ | commit 59358c8 (2026-05-20) |
| Hyperparam sweep regression detection automation | ✅ | PR#37 (2026-05-24) |
| Platform boundary case test coverage | ✅ | PR#37 (2026-05-24) + 116 tests |

**v4 DoD: 4/4 完成 ✅**

### 详细验证结果

| 层级 | 命令 | 预期 | 实际 |
|------|------|------|------|
| P0 | `python3 -m compileall .` | 无错误 | ✅ 通过 |
| P1 | `pytest tests/ -q --tb=short` | 100+ passed | ✅ 216 passed |
| P2 | `python3 -m benchmarks --quick` | acc≥0.70 | ✅ 0.79 |
| Depth-sweep | `python3 -m benchmarks.run --depth-sweep` | 27/30 | ✅ 27/30 |
| Hyperparam-sweep | CI hyperparam-sweep job | regressions=0 | ✅ 0 regressions |

---

## 决策

### 升级判定：v4 → v5

**结论**: 满足全部升级条件，批准进入 v5 阶段。

---

## v5 主题方向（预研，待第一轮 cron 细化）

以下为候选方向，v5 正式启动时由第一轮 cron 决策：

1. **自动化发行/发布流程** — GitHub Release 自动化、版本号管理、CHANGELOG 生成
2. **依赖安全审核** — pip-audit 集成、漏洞告警
3. **文档完整性自动化检查** — README/SPEC.md 同步验证、docstring 覆盖率
4. **README/SPEC.md 同步验证** — 确保文档与代码实现一致

### 暂不做（Non-Goals）

- 多语言 SDK
- AutoML / 超参搜索平台
- 模型生产部署托管

---

**历史**：
- 2026-05-25: Created (Accepted) — v4 DoD 4/4 完成 + PR#37 merged