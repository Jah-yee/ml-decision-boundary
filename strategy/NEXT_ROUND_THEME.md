# NEXT_ROUND_THEME.md — ml-decision-boundary v31 (v8 进行中)

**更新时间：** 2026-06-07 09:57 CST
**版本：** v31 (v8 DoD 细化完成)
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
| v8 Model Registry & Lifecycle | 🔄 进行中 | — |

---

## v8 DoD 细化（ADR-0013 — Proposed）

**主题：** Model Registry & Lifecycle（模型注册与生命周期管理）

### v8 DoD（ADR-0013）

| # | DoD 项目 | 描述 | 状态 |
|---|---------|------|------|
| 1 | Model Registry 核心 | 训练结果自动注册到 `~/.ml-decision-boundary/registry/`，元数据 JSON 持久化 | 🔄 待启动 |
| 2 | 模型序列化 | `save`/`load` 接口，支持插件模型和内置模型 | 🔄 待启动 |
| 3 | CLI 模型管理 | `ml-db model list` / `inspect <id>` / `delete <id>` | 🔄 待启动 |
| 4 | ADR-0013 Accepted 后同步 | NEXT_ROUND_THEME 更新 | 🔄 待启动 |

### 技术债务（v8 规划参考）

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C5 | 模型训练结果无持久化 | 每次运行独立，无版本追踪 | 🔄 v8 DoD #1 |
| C6 | benchmark 输出无结构化 registry | 回归检测依赖手动 | 🔄 v8 DoD #4 |
| C7 | 插件接口无版本声明机制 | 接口演化无约束 | 🔄 v8 DoD #2 附 |

---

## v31 早场完成项

- **ADR-0013 创建** ✅ — v8 DoD 细化文档（Model Registry & Lifecycle）
- **phases.md 更新** ✅ — v8 标记为进行中，ADR-0013 DoD #1 标记完成
- **spec/AGENT_CRON_PLAYBOOK.md** ✅ — 最小占位（原来不存在）
- **strategy/runs/2026-06-07-0957.md** ✅ — 早场运行报告

### PR 状态

| PR | 标题 | 状态 | 备注 |
|----|------|------|------|
| #53 | fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout | OPEN | 待皇上 merge |
| #54 | docs: v8 DoD 细化 — ADR-0013 Model Registry & Lifecycle | OPEN | 本轮 push 成功 |

---

## 下轮主题（v31 晚场 / v8 晚场）

**主题**：v8 DoD #1 启动 — Model Registry 核心实现

**待办**：
1. [ ] **PR#53 merge** — 需要皇上 review + approve
2. [ ] **v8 DoD #1 启动** — `core/registry.py` 实现
3. [ ] **RegistryManager 类** — 目录创建、元数据持久化
4. [ ] **ADR-0013 → Accepted** — 推动皇上审批

---

**版本历史**：
- v31 (2026-06-07 09:57): 早场 — v8 DoD 细化 ADR-0013 完成，v8 标记为进行中，AGENT_CRON_PLAYBOOK.md 占位
- v30 (2026-06-06 22:00): 晚场 — v7 完成，v8 规划启动，ADR-0012 Proposed，phases.md v8 入口定义
- v29 (2026-06-06 10:40): 早场 — v7 全部完成 ✅，C4 修复 PR#53，ADR-0011 → Accepted