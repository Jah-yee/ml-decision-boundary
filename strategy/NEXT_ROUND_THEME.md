# NEXT_ROUND_THEME.md — ml-decision-boundary v40 晚场 (v8 进行中)

**更新时间：** 2026-06-23 21:45 CST
**版本：** v40 晚场 (v8 DoD #1/#2/#3 ✅ — DoD #4 设计完成 ✅ — 等皇上 merge PR#53/#54/#55)
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
| v8 Model Registry & Lifecycle | 🔄 进行中 | — |

---

## v8 DoD（ADR-0013 — Proposed，DoD #1-4 全部完成/设计完成）

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
| C4 | pytest 超时不退出（完整 suite 内有一次重复 HANG） | P1 阻塞，CI 不可靠 | 🔄 PR#53 待 merge |
| C5 | 模型训练结果无持久化 | 每次运行独立，无版本追踪 | ✅ v8 DoD #1 完成 |
| C6 | benchmark 输出无结构化 registry | 回归检测依赖手动 | ✅ v8 DoD #4 设计完成（实现待启动） |
| C7 | 插件接口无版本声明机制 | 接口演化无约束 | ✅ v8 DoD #2 完成（get_state/from_state 协议） |

---

## v40 早场（2026-06-22 09:57 CST）

### 状态确认
- **P0**: ✅ compileall 无错误 + import smoke OK
- **P1**: ✅ exit 0（C4 偶发，本次通过）
- **ADR-0013**: DoD #1-4 全部完成/设计完成，Proposed 态，**等皇上 Accepted**
- **PR#53/#54/#55**: 全 OPEN（无 reviewDecision）
  - #53: 🔴 P1 阻塞修复，**请皇上 merge！**
  - #54: ADR governance 文档，请皇上 merge
  - #55: v8 核心功能，**请皇上 merge！**
- **本轮**: 无新代码（无法开发，P1/C4阻塞于 PR merge）— 完成 v40 早场状态确认

### PR 状态

| PR | 标题 | 状态 | 备注 |
|----|------|------|------|
| #53 | fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout | OPEN，无 reviewDecision | 🔴 **请皇上 merge！** — P1 阻塞 |
| #54 | docs: v7 complete — v8 governance setup (ADR-0012, phases.md v8 entry) | OPEN，无 reviewDecision | ADR governance 文档 |
| #55 | feat(core): v8 DoD #1/#2/#3 — Model Registry + plugin serialization + CLI management | OPEN，无 reviewDecision | 🔴 **请皇上 merge！** — v8 核心功能 |

---

## 下轮主题（v41 早场）

**主题**：v8 DoD #4 实现 — Benchmark Registry 结构化 + ADR-0013 → Accepted

**前提**：PR#53/#54/#55 merge 后 → ADR-0013 Accepted → v8 DoD #4 实现启动

**待办**：
1. [ ] **PR#53/#54/#55 merge** — 🔴 请皇上 review + approve！
2. [ ] **ADR-0013 → Accepted** — PR#54/#55 merge 后，ADR-0013 随 master 更新状态
3. [ ] **v8 DoD #4 实现启动** — `core/registry.py` 添加 benchmark 相关方法 + `benchmarks/run.py` 集成
4. [ ] **phases.md 更新** — v8 DoD #4 标记为进行中

---

## v40 晚场（2026-06-23 21:45 CST）

### 状态确认
- **P0**: ✅ compileall 无错误
- **P1**: ⚠️ HANG（EXIT:124，C4，PR#53 未 merge）
- **PR#53/#54/#55**: 全 OPEN（无 reviewDecision）
  - #53: 🔴 P1 阻塞修复，**请皇上 merge！**
  - #54: ADR governance 文档，请皇上 merge
  - #55: v8 核心功能，**请皇上 merge！**
- **本轮**: 无新代码（v8 DoD #4 依赖 PR#55 registry 基础设施，PR 未 merge 则无法开发）
- **git push**: ⚠️ 因 email privacy 限制失败，本地 commit 已完成

### PR 状态

| PR | 标题 | 状态 | 备注 |
|----|------|------|------|
| #53 | fix(tests): skip duplicate full-suite test to resolve C4 pytest timeout | OPEN，无 reviewDecision | 🔴 **请皇上 merge！** — P1 阻塞 |
| #54 | docs: v7 complete — v8 governance setup (ADR-0012, phases.md v8 entry) | OPEN，无 reviewDecision | ADR governance 文档 |
| #55 | feat(core): v8 DoD #1/#2/#3 — Model Registry + plugin serialization + CLI management | OPEN，无 reviewDecision | 🔴 **请皇上 merge！** — v8 核心功能 |

---

**版本历史**：
- v40 晚场 (2026-06-23 21:45): P0 ✅，P1 ⚠️ HANG（EXIT:124，C4，PR#53未merge），PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码，git push 因 email privacy 失败（本地 commit 已完成）
- v40 早场 (2026-06-22 09:57): P0 ✅，P1 ✅ exit 0（C4偶发，本次通过），PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码
- v39 晚场 (2026-06-21 21:54): P0 ✅，P1 ⚠️ HANG（EXIT:124，C4，PR#53未merge），PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码
- v39 早场 (2026-06-21 09:53): P0 ✅，P1 ✅ exit 0 within 60s（C4 偶发，本次通过），PR#53/#54/#55 全 OPEN，本轮无新代码
- v38 晚场 (2026-06-21 21:54): P0 ✅，P1 ⚠️ HANG（EXIT:124，C4，PR#53未merge），PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码
- v38 早场 (2026-06-21 09:53): P0 ✅，P1 ✅ exit 0 within 60s（C4 偶发，本次通过），PR#53/#54/#55 全 OPEN，本轮无新代码
- v37 晚场·二次 (2026-06-20 22:10): P0 ✅，P1 ⚠️ HANG（EXIT:124，C4偶发，PR#53未merge），PR#53/#54/#55 全 OPEN，本轮无新代码，完成 DoD #4 深度研究
- v37 晚场 (2026-06-20 10:30): P0 ✅，P1 ✅ 30s内 exit 0（本次测试意外通过；PR#53/#54/#55 全 OPEN），本轮无新代码
- v37 早场 (2026-06-19 09:46): P0 ✅，P1 ⚠️ HANG（C4,PR#53未merge），PR#53/#54/#55 全 OPEN，本轮无新代码
- v36 晚场·二次 (2026-06-18 21:49): P0 ✅，PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码，theme 更新
- v36 晚场 (2026-06-18 10:46): P0 ✅，PR#53/#54/#55 全 OPEN 无 reviewDecision，本轮无新代码
- v36 早场 (2026-06-17 09:47): **早场** — P0 ✅，PR#53/#54/#55 全 OPEN 等皇上 merge，本轮无新代码
- v35 (2026-06-16 21:52): **晚场** — ADR-0013 DoD #4 设计完成（P1 ⚠️ 因PR#53未merge），PR#53/#54/#55 等皇上 merge
- v35 (2026-06-16 09:38): 早场 — P0/P1 全绿（283 tests），ADR-0013 DoD #1-3 验证完成，PR#53/#54/#55 等皇上 review，v8 DoD #4 设计草案起草中
- v34 (2026-06-09 22:13): 早场 — v8 DoD #1-3 bugfix（list_models sort + svm_plugin typing），232 tests pass
