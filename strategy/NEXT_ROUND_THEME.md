# NEXT_ROUND_THEME.md — ml-decision-boundary v28 (v7 DoD #1 + #2 完成 ✅)

**更新时间：** 2026-06-03 21:50 CST
**版本：** v28 (v7 DoD #1 + #2 完成，晚场)
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
| v7 Extensibility, Edge Cases & UX | 🔄 进行中 | 2026-06-03 |

---

## v7 DoD（来自 ADR-0011）— 进行中

| # | DoD 项目 | 状态 | PR |
|---|---------|------|-----|
| 1 | 自定义模型插件接口 | ✅ PR#50 merged | daily/v7-evening-plugin-do1 |
| 2 | 数据集边界验证 | ✅ PR#51 OPEN | feature/v7-dod2-validation-clean |
| 3 | 错误信息改进 | ⏳ 待启动 | — |
| 4 | C4: pytest 超时修复 | ⏳ 待查 | — |
| 5 | ADR-0011 更新同步 | ⏳ 待完成 | — |

---

## ✅ 本轮完成（2026-06-03 晚场）

### PR 创建闭环

- **PR#51**：`feat(core): add dataset boundary validation — v7 DoD #2`
  - `core/validation.py` — validate_dataset() + validate_model_params()
  - `tests/test_validation.py` — 33 个测试用例
  - `main.py` — 接入边界验证

### 本地验证

- **P0**: compileall — ✅ pass
- **P0**: import main — ✅ OK
- **P1**: test_validation.py — ✅ 33 passed
- **P2**: benchmark smoke — ✅ SVM moons 正常运行

### v7 DoD #2 完成判定

> ADR-0011 DoD #2 全部验收标准满足 ✅
> 数据集边界验证可正常工作 ✅
> PR#51 已创建 ✅

---

## 📊 master / daily 分支状态

```
master:  251c509 docs: phase v6→v7 upgrade — ADR-0010
feature/v7-dod2-validation-clean: 848f4ff docs(strategy): v28 evening — PR#51 created, CHANGELOG updated
```

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常 | ✅ 已修复 |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | ✅ 已修复 |
| C4 | pytest 运行超时（120s+） | 非阻塞 | 待查 |

---

## 遗留未合并 PR

| # | 标题 | 状态 |
|---|------|------|
| 50 | feat(core/plugins): implement custom model plugin interface — v7 DoD #1 | OPEN |
| 49 | docs(adr): ADR-0011 — v7 DoD细化 | OPEN |
| 48 | docs: phase v6→v7 upgrade — ADR-0010 | OPEN |

---

## 下轮主题（v29 早场）

**主题**：v7 DoD #3 — 错误信息改进

**待办**：
1. [ ] **merge 等待中的 PR#48/49/50** — 需要人工 review + approve
2. [ ] **v7 DoD #3 启动** — 改进错误信息可读性和可操作性
3. [ ] **C4：pytest 超时调查** — 非阻塞，但值得查
4. [ ] **ADR-0011 更新为 Accepted** — 需在 PR merge 后完成

---

**版本历史**：
- v28 (2026-06-03 21:50): 晚场 — PR#51 创建，v7 DoD #2 完成 ✅，CHANGELOG 更新
- v27 (2026-06-01 09:45): 早场 — v7 规划开始，PR#48/49/50 创建
- v26 (2026-05-31 21:40): 晚场 — v6 完成，PR#47 merged