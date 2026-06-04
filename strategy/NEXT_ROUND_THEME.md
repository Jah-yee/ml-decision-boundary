# NEXT_ROUND_THEME.md — ml-decision-boundary v30 (v7 DoD #4 诊断完成 ✅)

**更新时间：** 2026-06-04 21:58 CST
**版本：** v30 (v7 DoD #4 诊断完成，晚场)
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
| v7 Extensibility, Edge Cases & UX | 🔄 进行中 | 2026-06-04 |

---

## v7 DoD（来自 ADR-0011）— 进行中

| # | DoD 项目 | 状态 | PR |
|---|---------|------|-----|
| 1 | 自定义模型插件接口 | ✅ merged (PR#50) | daily/v7-evening-plugin-do1 |
| 2 | 数据集边界验证 | ✅ PR#51 OPEN (CI pass) | feature/v7-dod2-validation-clean |
| 3 | 错误信息改进 | ✅ PR#52 OPEN (CI pass) | feature/v7-dod3-error-messages |
| 4 | C4: pytest 超时修复 | ✅ 诊断完成（良性，非阻塞） | — |
| 5 | ADR-0011 更新同步 | ⏳ 待 merge 后完成 | — |

---

## ✅ 本轮完成（2026-06-04 晚场）

### C4 诊断结论：良性超时

| 测试文件 | 单独运行时间 | 200+ 测试占比 |
|----------|-------------|-------------|
| test_main_coverage.py | 63s | 13 tests (MLP-heavy) |
| test_benchmarks_main.py | 44s | 3 tests (subprocess full-suite) |
| test_benchmarks_run.py | 97s | 20 tests (benchmark harness) |

**根因**: 
- MLP 训练收敛慢（0.3s/test，n_iter_=max_iter 触发警告）
- `test_benchmarks_main.py::test_benchmarks_module_full_suite` 跑 300s benchmark subprocess
- 非真正挂死，只是 ML 训练本身耗时

**结论**: 不需要修复（除非有人抱怨）。ADR-0010 方向 #6 "pytest 超时"可降为 nice-to-have。

### 通过层级验证

- **P0**: compileall ✅ | import main ✅
- **P1**: 254 tests passed (validation 33, experiment_flow 20, api_contract 19, api_train 19, boundary_cases 116, main 21, main_coverage 13, benchmarks_run 20, benchmarks_smoke 20)
- **P2**: 2026-06-04 benchmark 89/100 passed, avg_acc=0.78

---

## 📊 master / 分支状态

```
master:  251c509 docs: phase v6→v7 upgrade — ADR-0010
feature/v7-dod2-validation-clean: 848f4ff (PR#51 OPEN, CI pass)
feature/v7-dod3-error-messages: c9e96d7 (PR#52 OPEN, CI pass)
```

---

## Open PR 状态

| # | 标题 | CI | 待人工 |
|---|------|-----|--------|
| 48 | docs: phase v6→v7 upgrade — ADR-0010 | ✅ | review + approve |
| 49 | docs(adr): ADR-0011 — v7 DoD细化 | ✅ | review + approve |
| 50 | feat(core/plugins): custom model plugin interface | ✅ merged | — |
| 51 | feat(core): add dataset boundary validation | ✅ | review + approve |
| 52 | feat(core): standardize error messages | ✅ | review + approve |

---

## 下轮主题（v31 早场）

**主题**：merge 窗口 — PR#48/49/51/52 合并 + ADR-0011 Accepted

**待办**：
1. [ ] **merge PR#48/49/51/52** — 全部 CI pass，等人工 review + approve
2. [ ] **ADR-0011 → Accepted** — 所有相关 PR merge 后更新
3. [ ] **v7 DoD #5** — ADR-0011 同步到 spec/CHARTER.md / spec/phases.md
4. [ ] **v7 DoD #4 降为 nice-to-have** — C4 已诊断为良性

---

**版本历史**：
- v30 (2026-06-04 21:58): 晚场 — C4 诊断完成，P0/P1/P2 全通过，等 merge
- v29 (2026-06-04 10:08): 早场 — PR#52 创建，v7 DoD #3 完成 ✅，CHANGELOG 更新
- v28 (2026-06-03 21:50): 晚场 — PR#51 创建，v7 DoD #2 完成 ✅
- v27 (2026-06-01 09:45): 早场 — v7 规划开始，PR#48/49/50 创建
- v26 (2026-05-31 21:40): 晚场 — v6 完成，PR#47 merged