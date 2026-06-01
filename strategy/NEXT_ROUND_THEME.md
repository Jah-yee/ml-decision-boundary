# NEXT_ROUND_THEME.md — ml-decision-boundary v27 (v7 规划启动 ✅)

**更新时间：** 2026-06-01 09:45 CST
**版本：** v27 (v7 规划启动，早场)
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
| v6 Stability & Extensibility | ✅ 完成 | 2026-05-31 |
| v7 Extensibility, Edge Cases & UX | 🔄 进行中 | 2026-06-01 |

---

## v6 DoD（来自 ADR-0009）— 全部完成 ✅

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | respx/httpx 本地 env 冲突修复 | pytest collect 正常 | ✅ PR#42 merged |
| 2 | core/train_utils.py build_model 重复定义清理 | 文件无重复 def | ✅ PR#42 merged |
| 3 | API contract test 覆盖增强 | 15 tests, 400/500 errors | ✅ PR#44 merged |
| 4 | Release 自动化（GitHub Release） | CI on `v*` tag | ✅ PR#45 merged |
| 5 | README/SPEC.md 同步 v6 | 与 phases.md 一致 | ✅ PR#47 merged |

---

## v7 阶段入口（ADR-0010 Proposed）

**主题**：Extensibility, Edge Cases & UX

### v7 候选方向（待细化 — ADR-0011）

| # | 方向 | 描述 | 优先级 |
|---|------|------|--------|
| 1 | 自定义模型插件接口 | 用户可注册自己的模型 builder，无需修改核心代码 | P1 |
| 2 | 数据集边界验证 | 空数据集/单类数据集/极端值优雅处理 | P1 |
| 3 | 错误信息改进 | 当模型/数据集/参数异常时给出可操作的提示 | P1 |
| 4 | Benchmark 报告增强 | HTML 报告添加运行时环境、参数 hash 等元信息 | P2 |
| 5 | C4: pytest 超时修复 | sklearn MLP 收敛导致超时，诊断并修复 | P3 |

---

## ✅ 本轮完成（2026-06-01 早场）

### PR 创建闭环

- **PR#48**：`docs: phase v6→v7 upgrade — ADR-0010, Extensibility & Edge Cases theme`
  - v7 阶段注册（phases.md）
  - ADR-0010 新建（v6→v7 升级判定 + v7 方向提案）
  - 等待 merge

### 本地验证

- **P0**: compileall — ✅ pass
- **P1**: pytest test_api_contract.py — ✅ 15 passed (7s)

### v7 启动判定

> v6 DoD 全部 5 项完成 ✅ + ADR-0009 Accepted ✅
> v7 正式注册，ADR-0010 Proposed (等待 PR#48 merge)
> 下轮重点：ADR-0011 v7 DoD 细化

---

## 📊 master / daily 分支状态

```
master:  97fd01f docs(strategy): v26 — v6 complete, all DoD done, v7 planning starts
daily/v7-upgrade-adr0010: 4568919 docs: phase v6→v7 upgrade — ADR-0010 (PR#48)
```

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常 | ✅ 已修复 |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | ✅ 已修复 |
| C4 | pytest 运行超时（本地） | 非阻塞 | 待查 |

---

## 下轮主题（v27 晚场）

**主题**：v7 — DoD 细化与首项执行

**待办**：
1. [ ] **ADR-0011：v7 DoD 细化** — 基于 ADR-0010 方向，定义 v7 验收标准
2. [ ] **v7 DoD 首项启动** — 评估从 P1 哪项开始（插件接口/边界验证/错误信息）
3. [ ] **C4：pytest 超时调查** — 非阻塞，但值得查

---

**版本历史**：
- v27 (2026-06-01 09:45): 早场 — PR#48 创建，ADR-0010 proposed，v7 注册 ✅
- v26 (2026-05-31 21:40): 晚场 — PR#47 merged, v6 DoD 全部完成 ✅
- v25 (2026-05-31 09:58): 早场 — PR#45 创建，v6 DoD #4 + C3 完成，v6 DoD #5 部分完成
