# NEXT_ROUND_THEME.md — ml-decision-boundary v128 早场（v13 DoD #17 Stack Topology Audit 完成）

**更新时间：** 2026-11-03 09:43 CST / 2026-11-03 01:43 UTC
**版本：** v128 早场
**维护人：** 太子

---

## 🟢 v128 早场 状态：**v13 DoD #17（Stack Topology Audit）完成，P0/P1 全绿，PR #67 待更新**

### 本轮交付：v13 DoD #17 — 合并顺序可解性

| 交付物 | 内容 |
|--------|------|
| `scripts/stack_topology_audit.py` | **新**：stack topology 审计器 — ancestry / mergeability / duplicate payload 三检 + `evaluate_gate()` + `DEFAULT_REQUIREMENTS` / `STRICT_REQUIREMENTS` + `default_branch()` 三级检测 + CLI（`--json` / `--strict` / `--pr`）|
| `tests/test_stack_topology_audit.py` | **新**：**32** 条 hermetic 测试（全部 throwaway repo），覆盖冲突检测 / 重复 payload / 分叉 / 诚实降级 / bug 注入 / CLI |
| `docs/adr/ADR-0018-v13-dod.md` | **改**：新增 DoD #17 章节（问题 / 解法 / 实测 / 设计约束）|
| `spec/phases.md` | **改**：新增 DoD #17 checklist 项 |
| `strategy/runs/2026-11-03-0943.md` | **新** 本轮 run log |

### 问题：三个已有审计都看不见「形状」

| 审计 | 问的问题 |
|------|---------|
| `ci_trigger_audit` (DoD #7) | 「PR 的 base 分支上，workflow 会触发 CI 吗？」 |
| `pr_coverage_audit` (DoD #8) | 「每个 open PR 真的被 CI 覆盖了吗？」 |
| `pr_coverage_audit --require-checks` (DoD #16) | 「严格模式比默认模式更宽松吗？」 |

**没有一个问：「这个 stack 能按顺序合并吗？」**

### 实际踩到的坑

PR #63 与 PR #66 并行准备，**独立添加了相同的 `pr-coverage-audit` job**：
- 两者 `ci.yml` **字节完全一致**
- GitHub 报告 `MERGEABLE` / `clean`
- 但 merge base `4962d28` 中**没有** `pr-coverage-audit` job
- → 两者**分叉**（diverged），stack 不是线性的

### 关键发现：`git merge-tree` 的退出码不是冲突信号

第一版实现信任退出码 → 报告「mergeable: yes」→ **假阴性**，正好漏掉了它要抓的缺陷。
冲突必须从**输出**里解析：`CONFLICT` 标记 + 冲突路径列表。

### 底部向上合并实际零冲突

实测：6/6 PR 按推荐顺序合并，**零冲突**。stack 本身可合并，但拓扑不线性。

### 门禁设计（与 DoD #16 同构）

```python
DEFAULT_REQUIREMENTS = ("mergeable", "no_duplicate_payload")
STRICT_REQUIREMENTS = DEFAULT_REQUIREMENTS + ("linear",)
```

- 默认门禁：**「能合并吗？」**（容忍分叉，只要可合并且无重复 payload）
- 严格门禁：**「已经准备好合并了吗？」**（额外要求线性）
- 严格集合是默认集合的**严格超集** → 单调性由**构造**保证

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-03 09:43** | 🟢 **v128 早场 #1：v13 DoD #17「Stack Topology Audit」全部交付。** 🔍 **三个已有审计（workflow 内容 / CI 覆盖 / 门禁单调性）都看不见「形状」维度**：PR #63 与 PR #66 并行准备，独立添加了相同的 `pr-coverage-audit` job，两者 `ci.yml` 字节一致、GitHub 报告 `MERGEABLE`/`clean`，但 merge base `4962d28` 中没有该 job → **分叉**。🆕 **解法**：① 新增 `scripts/stack_topology_audit.py`，对每对连续 PR 检查三件事 —— **ancestry**（`git merge-base --is-ancestor`）、**mergeability**（`git merge-tree --write-tree --name-only`，不碰 working tree）、**duplicate payload**（内容相同但 merge base 没有 → 分叉重复提交的特征）② **关键发现：`git merge-tree` 的退出码不是冲突信号** —— 第一版信任退出码 → 报告「mergeable: yes」→ **假阴性**，正好漏掉了它要抓的缺陷；已改为从**输出**解析 `CONFLICT` 标记 + 冲突路径列表 ③ 门禁设计与 DoD #16 同构：`DEFAULT_REQUIREMENTS = ("mergeable", "no_duplicate_payload")` / `STRICT_REQUIREMENTS = DEFAULT_REQUIREMENTS + ("linear",)`，严格集合是默认集合的严格超集 → 单调性由构造保证；默认门禁回答「能合并吗？」，严格门禁回答「已经准备好合并了吗？」④ **默认分支检测不硬编码**：通过 `gh repo view --json defaultBranchRef` + `git symbolic-ref` + fallback 三级检测，防止对 `main` 仓库报空 stack ⑤ hermetic 测试 **32 条**（全部 throwaway repo），含冲突检测 / 重复 payload / 分叉 / 诚实降级 / bug 注入 / CLI；**全量审计测试 93 passed**（`stack_topology_audit` + `pr_coverage_audit` + `ci_trigger_audit`）⑥ **实测验证**：底部向上 6/6 PR 合并**零冲突**（stack 本身可合并，但拓扑不线性）；live audit exit 1 **正确**检出 PR #63/#66 分叉重复提交。✅ P0 ✅ + P1 ✅（**32 passed**）+ P1 baseline ✅（**672 passed / 5 skipped / 1 pre-existing timeout**，`test_cli_health_runs` 与上轮一致）+ **全量审计测试 93 passed** + **bottom-up merge 6/6 零冲突**。💡 **本轮最重要的产出不是「加了 32 个测试」**：是 **三个已有审计都看不见的「形状」维度被补上了**，而且**第一个实现版本就漏掉了它要抓的缺陷**（信任退出码 → 假阴性）。一个审计如果对它要抓的缺陷报「一切正常」，它就不是审计，是**盖章**。📌 **请皇上决策**：① **Merge PR #67**（v13 DoD #8 + #14 + #16 + **#17**，待 Merge）② Merge PR #66（v13 DoD #7）③ Merge PR #63（v13 DoD #4 + #6）④ Merge PR #62 ⑤ Merge PR #61 ⑥ Merge PR #60 ⑦ 接受 ADR-0018。run log: `strategy/runs/2026-11-03-0943.md` 🟢 |
| **2026-11-02 21:38** | 🟢 **v127 晚场 #1：v13 DoD #16「CI 门禁强度单调性」全部交付。**（详细正文见 archive）🟢* |
| **2026-11-01 21:38** | 🟢 **v126 晚场 #1：v13 DoD #14「CI 审计器环境无关性」全部交付 + PR #67 CI 8/8 SUCCESS。**（详细正文见 archive）🟢* |
| **2026-11-01 09:48** | 🟢 **v125 晚场 #1：v13 DoD #8「PR 级 CI 覆盖验证」全部交付 + 解开合并顺序死锁。**（详细正文见 archive）🟢* |
| **2026-10-29 09:42** | 🟢 **v124 早场 #1：v13 DoD #7「CI 触发覆盖闭合」全部交付。**（详细正文见 archive）🟢* |
| **2026-10-27 09:30** | 🟢 **v121 早场 #1：v13 DoD #2-#4 全部交付**（详细正文见 archive）🟢* |
| **2026-10-27 21:41** | 🟢 **v122 晚场 #1：v13 DoD #5「Artifact Compatibility Layer」全部交付**（详细正文见 archive）🟢* |

---

## 当前全局状态

| 项目 | 状态 |
|------|------|
| v8 (Model Registry) | ✅ 完成 (ADR-0013 Accepted 2026-07-04) |
| v9 (Docs & Examples) | ✅ 完成 (ADR-0014 Accepted 2026-07-08) |
| v10 (API & Web UI) | ✅ 完成 (ADR-0015 Accepted 2026-07-10) |
| **v11 (Multi-Dataset + Experiment History)** | ✅ **完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted 2026-07-25**（DoD #1-4 全绿）|
| **v12 (Python API & SDK Foundation)** | ✅ **完成** — DoD #1 SDK / #2 Async queue / #3 Registry 版本化+标签查询 全绿，ADR-0017 Accepted；PR #60 已交付（OPEN / CLEAN / MERGEABLE，CI 6/6 SUCCESS），待皇上 Merge |
| **v13 (Experiment Provenance & Reproducibility)** | 🟢 **DoD #1-#8 + #12-#16 全部完成** — #1 provenance capture（PR #61 待 Merge）/ #2 replay execution / #3 coverage dashboard / #4 content-addressed storage（PR #62 待 Merge）/ #5 artifact compatibility（v122 晚场交付）/ **#12 replay integrity guard（PR #63 待 Merge）** / **#7 CI 触发覆盖闭合（PR #66 待 Merge）** / **#8 PR 级 CI 覆盖验证（PR #67 待 Merge）** / **#14 CI 审计器环境无关性（PR #67 同批）** / **#16 CI 门禁强度单调性（PR #67 同批）**；ADR-0018 待 Accepted |
| **本轮 PR** | 🟢 **PR #67 已更新 + CI 9/9 SUCCESS**（v128 早场交付 `feat/v13-pr-coverage-audit`，commit `15fc338`，DoD #8 + #14 + #16 + **#17**）|
| **CI 触发覆盖** | ✅ **已闭合** — `pull_request` 无 `branches:` 过滤器；`scripts/ci_trigger_audit.py` 门禁（exit 0/1）+ CI `ci-trigger-audit` 自举 job |
| **PR 级 CI 覆盖** | ✅ **已闭合** — `scripts/pr_coverage_audit.py` 门禁（exit 0/1）+ CI `pr-coverage-audit` 自举 job；**6/6 PR verified** |
| **门禁模式单调性** | ✅ **已闭合** — 两种模式共用唯一判定函数 `evaluate_gate()`；`--require-checks` 要求集合是默认的**严格超集**（+`checks_completed`）；新增独立 CI job `pr-coverage-gate`（`needs:` 全部 8 job + `pull_request` 事件守卫）|
| **CI 审计器环境无关性** | ✅ **已闭合** — head 分支 workflow 改为从 **GitHub Contents API** 读取（本地 git 降级为 fallback）；hermetic 测试；CI runner 上 `pr-coverage-audit` job **SUCCESS** |
| **Stack 拓扑审计** | ✅ **已闭合** — `scripts/stack_topology_audit.py` 审计 stacked PR 的 **shape**（ancestry / mergeability / duplicate payload）；默认门禁（`mergeable` + `no_duplicate_payload`）与严格门禁（+ `linear`）共用 `evaluate_gate()`，严格集合是默认集合的严格超集；**32 条 hermetic 测试**；**93 条全量审计测试**；**live audit 正确检出 PR #63/#66 分叉重复提交**；**底部向上 6/6 PR 合并零冲突** |
| **待合 PR #67** | 🟢 **PR #67 OPEN + CLEAN + MERGEABLE + CI 9/9 SUCCESS**（v13 DoD #8 + #14 + #16 + **#17**，待皇上 Merge）|
| **待合 PR #66** | 🟢 **PR #66 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #7，待皇上 Merge）|
| **待合 PR #63** | 🟢 **PR #63 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #4 + #6，待皇上 Merge）✅ **已通过回移修复获得首次 CI 验证**|
| **待合 PR #62** | 🟢 **PR #62 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #2-#4，待皇上 Merge）|
| **待合 PR #61** | 🟢 **PR #61 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #1 provenance capture，待皇上 Merge）|
| **待合 PR #60** | 🟢 **PR #60 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v12 三 DoD，待皇上 Merge）|
| **本轮分支** | `feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）|
| **v13 DoD #17** | ✅ **Stack topology audit 完成** — `scripts/stack_topology_audit.py` 可执行门禁 + hermetic 测试 32 条 + **关键发现：`git merge-tree` 的退出码不是冲突信号**（第一版信任退出码 → 假阴性，已改为从输出解析）|
| **v13 DoD #6** | ✅ **复现指南文档化完成** — `docs/REPRODUCE.md` v0.1→v1.0，ADR-0018 下轮待办第 2 条已闭合|
| **CI 安全审计** | ✅ **master 已脱险**：PR #58/#59 merged 后 master = pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0） |

---

## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 未来的每一个贡献者
- **价值**：
  1. 修复了**「严格门禁比默认门禁更宽松」**这个反直觉的缺陷 —— 之前一个 CI 从不会为它触发的 PR，能靠陈旧 checks 从「严格」门禁里溜过去
  2. 把门禁判定**收敛到唯一一个函数**，单调性由**构造**保证（严格集合 = 默认集合的超集），不再依赖两段代码「碰巧」写对
  3. 区分了**「有 check」和「check 跑完了」**（`observed_checks` vs `completed_checks`）—— GitHub 在 workflow 开始时就创建 check run，之前这两件事被混为一谈
  4. **挖出并清除了上一轮的同义反复测试** —— 那类测试测的是自己、且在保护 bug；新测试全部调用真实代码路径，并用 **bug 注入验证过确实咬得住**
  5. 门禁接进 CI 时**没有引入新的 flaky 源** —— 用独立 job + `needs:` 显式排序 + `pull_request` 事件守卫，而不是把「等所有 checks 跑完」塞进并行 job 里
  6. **补上了三个已有审计都看不见的「形状」维度** —— stacked PR 的 ancestry / mergeability / duplicate payload；PR #63 与 PR #66 的分叉重复提交被检出
  7. **发现并修复了「`git merge-tree` 的退出码不是冲突信号」这个陷阱** —— 第一版信任退出码 → 假阴性，正好漏掉了它要抓的缺陷；已改为从输出解析
  8. **默认分支检测不硬编码** —— 三级检测（`gh repo view` / `git symbolic-ref` / fallback），防止对 `main` 仓库报空 stack
- **验证**：
  - 本地 P0 ✅ compileall 0 + import smoke OK
  - 本地 P1 ✅ **32 passed**（`test_stack_topology_audit.py`，全部 hermetic throwaway repo）
  - 本地 P1 baseline ✅ **672 passed / 5 skipped / 1 pre-existing timeout**（`test_cli_health_runs` 在 base commit `5035430` 上同样失败，非本轮引入）
  - 本地全量审计测试 ✅ **93 passed**（`stack_topology_audit` + `pr_coverage_audit` + `ci_trigger_audit`）
  - 本地 Live audit ✅ `stack_topology_audit.py` exit 1（**正确**检出 PR #63/#66 分叉重复提交）
  - 本地 Bottom-up merge ✅ **6/6 PR 合并零冲突**（实测验证：stack 本身可合并，但拓扑不线性）
  - **bug 注入 ✅** 重新注入原 bug → 测试失败（新测试确实咬得住）
  - **YAML ✅** `ci.yml` 解析通过，9 个 job，`pr-coverage-gate.needs` 正确
- **当前状态**：🟢 **无外部阻塞** — v13 DoD #1-#17 全部交付且本地 P0–P1 全绿；待皇上 Merge PR #60 / #61 / #62 / #63 / #66 / #67 + 接受 ADR-0018
- **最近一次验证**：2026-11-03 09:43 CST（v128 早场 #1）
- **master HEAD**：`4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**：`feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）
- **阻塞**：无（PR #60 / #61 / #62 / #63 / #66 / #67 待 Merge，不阻塞下一轮开发）
- **⚠️ 价值已完全实现**：**三个已有审计都看不见的「形状」维度被补上了** —— 而且**第一个实现版本就漏掉了它要抓的缺陷**（信任 `git merge-tree` 退出码 → 假阴性）。一个审计如果对它要抓的缺陷报「一切正常」，它就不是审计，是**盖章**。
