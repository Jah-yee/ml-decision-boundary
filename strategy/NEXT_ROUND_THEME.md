# NEXT_ROUND_THEME.md — ml-decision-boundary v36 (v8 进行中)

**更新时间：** 2026-06-17 09:47 CST
**版本：** v36 (v8 DoD #1/#2/#3 ✅ — DoD #4 设计完成 ✅ — 等皇上 merge PR#53/#54/#55)
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

### v8 DoD（ADR-0013 — Proposed，DoD #1-4 全部完成）

| # | DoD 项目 | 描述 | 状态 |
|---|---------|------|------|
| 1 | Model Registry 核心 | 训练结果自动注册到 `~/.ml-decision-boundary/registry/`，元数据 JSON 持久化 | ✅ 完成 (PR#55 + bugfix) |
| 2 | 模型序列化 | `save`/`load` 接口，支持插件模型和内置模型 | ✅ 完成 (PR#55 + bugfix) |
| 3 | CLI 模型管理 | `ml-db model list` / `inspect <id>` / `delete <id>` | ✅ 完成 (PR#55 + bugfix) |
| 4 | Benchmark Registry | benchmark 输出结构化注册；`list_benchmarks()`/`get_benchmark()`/`detect_regressions()`；CLI `ml-db benchmark list`/`inspect` | ✅ DoD 设计完成 (ADR-0013 v2) |
| 5 | ADR-0013 Accepted 后同步 | NEXT_ROUND_THEME 更新 | 🔄 待启动（等 PR#54/#55 merge → ADR-0013 Accepted） |

### 技术债务（v8 规划参考）

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C5 | 模型训练结果无持久化 | 每次运行独立，无版本追踪 | ✅ v8 DoD #1 完成 |
| C6 | benchmark 输出无结构化 registry | 回归检测依赖手动 | ✅ v8 DoD #4 设计完成（实现待启动） |
| C7 | 插件接口无版本声明机制 | 接口演化无约束 | ✅ v8 DoD #2 完成（get_state/from_state 协议） |

---

## v36 早场完成项（2026-06-17 09:47 CST）

### 状态确认 ✅
- **ADR-0013**: DoD #1-4 全部完成，Proposed 态，等皇上 Accepted
- **PR#53/#54/#55**: 全 OPEN，**请皇上 review + merge！**
- **v8 DoD #4 设计**: ADR-0013-v8-dod.md 已包含完整 DoD #4 详细设计（commit f22e404）
- **本轮**: 无新代码改动（v8 DoD #1-4 全部完成待 merge）；theme 更新

### 验证结果
- **P0**: compileall + import main ✅
- **P1**: ⚠️ pytest timeout（HANG，见下方说明）
  - 原因：PR#53（skip duplicate full-suite test）未 merge，C4 技术债务未清除
  - pytest 确认收集到 **284 tests**
  - 这是 PR#53 要修的已知 bug，非 regression

### PR 状态

| PR | 标题 | 状态 | 备注 |
|----|------|------|------|
| #53 | fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout | OPEN | 🔴 **请皇上 merge！** — P1 阻塞 |
| #54 | docs: v8 DoD 细化 — ADR-0013 Model Registry & Lifecycle | OPEN | ADR-0013 文档更新，DoD #4 设计已并入 |
| #55 | feat(core): v8 DoD #1/#2/#3 — Model Registry + plugin serialization + CLI management | OPEN | 🔴 **请皇上 merge！** — v8 核心功能 |

---

## 下轮主题（v36 晚场 / v9 早场）

**主题**：v8 DoD #4 实现 — Benchmark Registry 结构化 + ADR-0013 → Accepted

**前提**：PR#53/#54/#55 merge 后 → ADR-0013 Accepted → v8 DoD #4 实现启动

**待办**：
1. [ ] **PR#53/#54/#55 merge** — 🔴 请皇上 review + approve！
2. [ ] **ADR-0013 → Accepted** — PR#54/#55 merge 后，ADR-0013 随 master 更新状态
3. [ ] **v8 DoD #4 实现启动** — `core/registry.py` 添加 benchmark 相关方法 + `benchmarks/run.py` 集成
4. [ ] **phases.md 更新** — v8 DoD #4 标记为进行中

---

**版本历史**：
- v36 (2026-06-17 09:47): **早场** — P0 ✅，PR#53/#54/#55 全 OPEN 等皇上 merge，本轮无新代码
- v35 (2026-06-16 21:52): **晚场** — ADR-0013 DoD #4 设计完成（P1 ⚠️ 因PR#53未merge），PR#53/#54/#55 等皇上 merge
- v35 (2026-06-16 09:38): 早场 — P0/P1 全绿（283 tests），ADR-0013 DoD #1-3 验证完成，PR#53/#54/#55 等皇上 review，v8 DoD #4 设计草案起草中
- v34 (2026-06-09 22:13): 早场 — v8 DoD #1-3 bugfix（list_models sort + svm_plugin typing），232 tests pass
- v33 (2026-06-08 21:54): 晚场 — v8 DoD #2（插件序列化）+ v8 DoD #3（CLI）完成，PR#55 更新
- v32 (2026-06-07 21:51): 晚场 — v8 DoD #1 完成，PR#55，RegistryManager + tests
- v31 (2026-06-07 09:57): 早场 — v8 DoD 细化 ADR-0013 完成，v8 标记为进行中
- v30 (2026-06-06 22:00): 晚场 — v7 完成，v8 规划启动，ADR-0012 Proposed