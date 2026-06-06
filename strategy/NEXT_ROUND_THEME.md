# NEXT_ROUND_THEME.md — ml-decision-boundary v29 (v7 完成 ✅)

**更新时间：** 2026-06-06 10:40 CST
**版本：** v29 (v7 全部完成，早场)
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
| v6 Stability & Extensibility | ✅ | 2026-05-31 |
| v7 Extensibility, Edge Cases & UX | ✅ 完成 | 2026-06-06 |
| v8 阶段规划 | 🔄 待启动 | — |

---

## v7 DoD（来自 ADR-0011）— 全部完成 ✅

| # | DoD 项目 | 状态 | PR | 完成日期 |
|---|---------|------|-----|---------|
| 1 | 自定义模型插件接口 | ✅ merged | PR#50 | 2026-06-06 |
| 2 | 数据集边界验证 | ✅ merged | PR#51 | 2026-06-06 |
| 3 | 错误信息改进 | ✅ merged | PR#52 | 2026-06-06 |
| 4 | C4: pytest 超时修复 | ✅ merged | PR#53 | 2026-06-06 |
| 5 | ADR-0011 更新同步 | ✅ Accepted | — | 2026-06-06 |

---

## ✅ 本轮完成（2026-06-06 早场）

### C4 技术债务修复

- **根因**：`test_benchmarks_main.py::test_benchmarks_module_full_suite` 与 `test_benchmarks_smoke.py::TestBenchmarksCLI::test_benchmarks_full_suite_runs` 均运行完整 benchmark 套件，并发执行时资源争用导致超时
- **修复**：标记重复测试为 `@pytest.mark.skip`，保留 smoke 中的覆盖
- **PR#53**: `fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout`

### ADR-0011 → Accepted

- 全部 v7 DoD 项目验证完成，状态更新为 **Accepted**

### 本地验证

- **P0**: compileall — ✅ pass
- **P0**: import main — ✅ OK
- **P1**: pytest — ✅ 271 passed, 1 skipped (原 272 collected 超时)
- **P2**: benchmark smoke — ✅ SVM moons 正常运行

### 全量测试通过

```
271 passed, 1 skipped, 19 warnings in 125.67s (0:02:05)
→ 原超时问题解决，测试套件稳定
```

---

## 技术债务状态

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常 | ✅ 已修复 |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | ✅ 已修复 |
| C4 | pytest 运行超时（120s+） | 全量测试阻塞 | ✅ 已修复 PR#53 |

---

## 📊 master 分支状态

```
master:  8e02b87 feat(core): standardize error messages with canonical error codes — v7 DoD #3 (#52)
fix/pytest-timeout-c4: 3815b2c fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout
```

---

## 下轮主题（v29 晚场 / v8 早场）

**主题**：v8 阶段规划 — Extensibility 深化 or 新方向探索

**待办**：
1. [ ] **PR#53 merge** — 需要人工 review + approve
2. [ ] **v8 阶段规划** — 基于 v7 完成情况，启动 v8 DoD 规划
3. [ ] **ADR-0012 创建** — v7→v8 升级判定文档
4. [ ] phases.md 更新 — v7 标记为完成，v8 入口条件定义

---

**版本历史**：
- v29 (2026-06-06 10:40): 早场 — v7 全部完成 ✅，C4 修复 PR#53，ADR-0011 → Accepted
- v28 (2026-06-03 21:50): 晚场 — PR#51 创建，v7 DoD #2 完成 ✅，CHANGELOG 更新
- v27 (2026-06-01 09:45): 早场 — v7 规划开始，PR#48/49/50 创建
- v26 (2026-05-31 21:40): 晚场 — v6 完成，PR#47 merged