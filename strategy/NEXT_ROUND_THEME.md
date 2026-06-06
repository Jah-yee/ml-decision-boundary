# NEXT_ROUND_THEME.md — ml-decision-boundary v30 (v8 规划)

**更新时间：** 2026-06-06 22:00 CST
**版本：** v30 (v7 完成，v8 规划启动)
**维护人：** 太子

---

## 📋 当前阶段状态

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| v0 Foundation | ✅ | 2026-04-26 |
| v1 Testing& Harness | ✅ | 2026-04-29 |
| v2 Model & Data Expansion | ✅ | 2026-05-06 |
| v3 Platform | ✅ | 2026-05-19 |
| v4 Reproducibility & Robustness | ✅ | 2026-05-24 |
| v5 Automation & Documentation | ✅ | 2026-05-27 |
| v6 Stability & Extensibility | ✅ | 2026-05-31 |
| v7 Extensibility, Edge Cases & UX | ✅ 完成 | 2026-06-06 |
| v8 Model Registry & Lifecycle | 🔄 规划中 | — |

---

## v7 完成总结（2026-06-06 晚场收尾）

### v7 DoD（ADR-0011）— 全部完成 ✅

| # | DoD 项目 | 状态 | PR | 完成日期 |
|---|---------|------|-----|---------|
| 1 | 自定义模型插件接口 | ✅ merged | PR#50 | 2026-06-06 |
| 2 | 数据集边界验证 | ✅ merged | PR#51 | 2026-06-06 |
| 3 | 错误信息改进 | ✅ merged | PR#52 | 2026-06-06 |
| 4 | C4: pytest 超时修复 | ✅ merged | PR#53 | 2026-06-06 |
| 5 | ADR-0011 更新同步 | ✅ Accepted | — | 2026-06-06 |

### 本轮完成（晚场）

- **ADR-0012 创建** — v7→v8 升级判定文档 Proposed
- **phases.md 更新** — v7 标记为完成，v8 入口条件定义
- **PR#46 关闭** — v6 readme sync 已 stale，关闭
- **PR#53** — 待皇上 review + approve + merge

### master 分支状态

```
master:  8e02b87 feat(core): standardize error messages with canonical error codes — v7 DoD #3 (#52)
fix/pytest-timeout-c4: d5ae6c4 docs(strategy): v29 morning run report
```

---

## v8 阶段规划（ADR-0012 — Proposed）

**主题：** Model Registry & Lifecycle（模型注册与生命周期管理）

### v8 候选 DoD（待细化 ADR-0013）

| # | DoD 项目 | 描述 | 优先级 |
|---|---------|------|--------|
| 1 | Model Registry 核心 | 训练结果自动注册到 `~/.ml-decision-boundary/registry/`，元数据 JSON 持久化 | P1 |
| 2 | 模型序列化 | `save`/`load` 接口，支持插件模型和内置模型 | P1 |
| 3 | CLI 模型管理 | `ml-db model list` / `inspect <id>` / `delete <id>` | P1 |
| 4 | Benchmark Registry | benchmark 结果写入 registry，支持回归趋势查询 | P2 |
| 5 | ADR-0012 Accepted 后同步 | NEXT_ROUND_THEME 更新 | P0 |

### 技术债务（v8 规划参考）

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C5 | 模型训练结果无持久化 | 每次运行独立，无版本追踪 | 🔄 v8 DoD #1 |
| C6 | benchmark 输出无结构化 registry | 回归检测依赖手动 | 🔄 v8 DoD #4 |
| C7 | 插件接口无版本声明机制 | 接口演化无约束 | 🔄 v8 DoD #2 附 |

---

## 下轮主题（v30 早场 / v8 早场）

**主题**：v8 DoD 细化 + ADR-0013 创建

**待办**：
1. [ ] **PR#53 merge** — 需要皇上 review + approve
2. [ ] **ADR-0013 创建** — v8 DoD 细化文档
3. [ ] **v8 DoD #1 启动** — Model Registry 核心设计与实现
4. [ ] **phases.md 更新** — v8 标记为进行中

---

**版本历史**：
- v30 (2026-06-06 22:00): 晚场 — v7 完成，v8 规划启动，ADR-0012 Proposed，phases.md v8 入口定义
- v29 (2026-06-06 10:40): 早场 — v7 全部完成 ✅，C4 修复 PR#53，ADR-0011 → Accepted
