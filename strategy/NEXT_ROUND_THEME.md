# NEXT_ROUND_THEME.md — ml-decision-boundary v131 晚场（v13 stack 拓扑缺陷已修复：5/5 links linear）

**更新时间：** 2026-11-05 21:30 CST / 2026-11-05 13:30 UTC
**版本：** v131 晚场
**维护人：** 太子
**本轮 run log：** `strategy/runs/2026-11-05-2130.md`

---

## 🟢 v131 晚场 状态：**v13 stack 拓扑缺陷已修复 —— 6 个 PR 现在可以自底向上安全合并**

### 本轮交付：v131 晚场 — 修复 `diverged-duplicate` 拓扑缺陷，让整条 v13 stack 可合并

| 交付物 | 内容 |
|--------|------|
| **根因定位** | PR #63 与 PR #66 的 head 分支**各自独立提交了同一个 CI trigger 修复**（`524718a` / `f8a9d8c`），文件内容**逐字节相同**（sha256 校验 `dc8d67a6…` / `6f1e1c82…`）→ 属重复提交，丢弃其一不丢内容 |
| **修复** | `git cherry-pick` 重放提交链：`#66` → `e3d5626`；`#67` 13 个独有提交 → `833bcf6`；树内容 `git diff` 为空 = 与原 head 完全等价 |
| **GH007 规避** | rebase 保留 author 但 committer 写成私有邮箱 → 改用 `cherry-pick` + 显式设 `GIT_COMMITTER_EMAIL`/`GIT_AUTHOR_EMAIL` 为已验证公开地址 |
| **push** | `--force-with-lease`（先 `ls-remote` 读真实 sha 作期望值）→ 远端回读校验 #66=`e3d5626`、#67=`833bcf6` |
| **`stack_topology_audit.py --strict`** | ✅ **exit 0 — 5/5 links clean，0 repairable，0 blocked** |
| **CI** | #66 **7/7 SUCCESS**、#67 **10/10 SUCCESS**；6 个 PR 全部 MERGEABLE/CLEAN，0 失败 0 pending |
| `strategy/runs/2026-11-05-2130.md` | **新**：本轮 run log |

### 动手前的复核（不轻信上一轮的自我报告）

| 检查 | 结果 |
|------|------|
| `spec/phases.md` | v13 DoD #1–#18 **全部 `[x]`，v13 已收口** |
| open PR 队列 | 6 个，**全部 MERGEABLE/CLEAN + CI 全绿** |
| master HEAD | `4082158`（PR #59）—— **v12 SDK 与整个 v13 阶段都还没进 master** |
| `stack_topology_audit.py --strict` | ❌ **exit 1 — PR #63/#66 diverged-duplicate** |

→ **代码侧 DoD 已全部完成，但没有任何一个 PR 被合并。** 本轮最高价值动作不是「再写一个 DoD」，
而是**让已完成的 DoD 真正落地**（v13 收口到 master）。

### 本轮的元观察

「完成」与「交付」的缝，这轮又出现了一次，只是换了个位置：

- **v130 早场**修的是「代码 staged 了但没 commit」（代码 → 版本库）
- **v131 晚场**修的是「版本库里有了但 PR 分叉了」（版本库 → 可合并）

**两个缺陷在同一个位置：stack 的最后一环。** 6 个 PR 全部 CLEAN 全部 CI 全绿，
看起来「只差皇上点一下 Merge」—— 但**有一个 PR 实际上不可按建议顺序合并**。
**绿色的 CI 和 CLEAN 的 mergeable 状态都不能证明「能合并」，只有拓扑审计能。**

**另一个观察：「已修复」本身也需要证据。** push 成功 ≠ 审计器能看见 ——
`stack_topology_audit.py` 解析的是**裸分支名**（不是 `origin/<branch>`），
本地 ref 没同步时它会对着旧 ref 报**旧缺陷**，让人误以为修复失败而去做多余的手工改动。

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-05 09:36** || **2026-11-05 21:30** | 🟢 **v131 晚场 #1：修复 v13 stack 的 `diverged-duplicate` 拓扑缺陷，6 个 PR 现在可自底向上安全合并。** 🔍 **动手前复核**：v13 DoD #1–#18 全部 `[x]` 且 6 个 PR 全部 CLEAN+CI 全绿，但 **master HEAD 仍是 `4082158`（PR #59）—— v12 SDK 与整个 v13 阶段都还没进 master** → 本轮最高价值动作不是「再写一个 DoD」，而是**让已完成的 DoD 真正落地**。🩹 **根因**：PR #63 与 PR #66 的 head 分支**各自独立提交了同一个 CI trigger 修复**（`524718a` / `f8a9d8c`），文件内容**逐字节相同**（sha256 校验 `dc8d67a6…` / `6f1e1c82…`）→ 属重复提交而非真实分歧，丢弃其一**不丢任何内容**。🛠 **修复**：按 audit 自己给出的方案用 `git cherry-pick` 重放提交链（#66 → `e3d5626`，#67 的 13 个独有提交 → `833bcf6`），重放后 `git diff` **为空** = 树内容与原 head 完全等价。🐚 **三个坑**：① **GH007** —— rebase 保留 author 但 **committer 被写成私有邮箱** → 改用 `cherry-pick` + 显式设 `GIT_COMMITTER_EMAIL`/`GIT_AUTHOR_EMAIL` 为已验证公开地址；② **`--force-with-lease` 期望值要现读** —— 我以为远端 head 是 `f004255`，实际是 `36a6dd3` → 先 `git ls-remote` 读真实 sha 再作 lease，推完**立刻回读校验**；③ **audit 解析的是裸分支名不是 `origin/`** —— push 成功后 audit 仍报旧缺陷，因为本地 ref 没同步 → `git fetch --prune` + `git branch -f` 对齐后 audit 才通过。✅ **验收**：`stack_topology_audit.py --strict` **exit 0 — 5/5 links clean, 0 repairable, 0 blocked**（**audit 自己给的修复方案，跑完 audit 自己就通过**）+ P0 compileall ✅ + P1 **155 passed** + live `ci_trigger_audit` exit 0 + live `job_graph_audit --strict` exit 0 + 远端 sha 回读 #66=`e3d5626` / #67=`833bcf6` + **CI #66 7/7 SUCCESS、#67 10/10 SUCCESS**，6 个 PR 全部 MERGEABLE/CLEAN 0 失败 0 pending。💡 **元观察**：「完成」与「交付」的缝这轮又出现一次，只是换了位置 —— v130 早场修的是「代码 staged 了但没 commit」，v131 晚场修的是「版本库里有了但 PR 分叉了」，**两个缺陷在同一个位置：stack 的最后一环**。6 个 PR 全部 CLEAN 全部 CI 全绿，看起来「只差点一下 Merge」，但**有一个 PR 实际上不可按建议顺序合并** —— **绿色的 CI 和 CLEAN 的 mergeable 状态都不能证明「能合并」，只有拓扑审计能**。📌 **请皇上决策**：按 CHARTER 第 7 步「等 Merge（由人工/自动合并）」，合并权不在本代理，故本轮**只修复不合并**。请皇上依次 Merge：**#60 → #61 → #62 → #63 → #66 → #67**（**必须自底向上**）+ 确认 ADR-0018 Accepted。run log: `strategy/runs/2026-11-05-2130.md` 🟢 |
| **2026-11-04 21:30** | 🟢 **v129 晚场 #1：v13 DoD #18「Job Dependency Graph Audit」全部交付。** 新增 `scripts/job_graph_audit.py`（676 行纯 stdlib），检 dangling `needs:` / `needs:` cycle / ungated verification job 三个缺陷；门禁同构（严格集合 = 默认集合严格超集）；hermetic 测试 **62 条**；全量审计 **155 passed**；CI 新增 `job-graph-audit` job 并接入 `pr-coverage-gate.needs`；live `--strict` exit 0。（正文见 archive）🟢* |
| **2026-11-03 21:30** | 🟢 **v128 晚场 #1：v13 DoD #17 CI 修复完成。** 3 条 CLI 测试改为 hermetic（fake `gh`，不注入 `GH_TOKEN`）；CI run `41646891602` **9/9 SUCCESS**。（正文见 archive）🟢* |
| **2026-11-03 09:43** | 🟢 **v128 早场 #1：v13 DoD #17「Stack Topology Audit」全部交付。** 新增 `scripts/stack_topology_audit.py`（ancestry / mergeability / duplicate payload）；关键发现 `git merge-tree` 退出码不是冲突信号（改为解析输出）；hermetic 测试 **32 条**；全量审计 **93 passed**；bottom-up 合并 6/6 零冲突。（正文见 archive）🟢* |
| **2026-11-02 21:38** | 🟢 **v127 晚场 #1：v13 DoD #16「CI 门禁强度单调性」全部交付。**（详细正文见 archive）🟢* |
| **2026-11-01 21:38** | 🟢 **v126 晚场 #1：v13 DoD #14「CI 审计器环境无关性」全部交付 + PR #67 CI 8/8 SUCCESS。**（详细正文见 archive）🟢* |

## 当前全局状态

| 项目 | 状态 |
|------|------|
| v8 (Model Registry) | ✅ 完成 (ADR-0013 Accepted 2026-07-04) |
| v9 (Docs & Examples) | ✅ 完成 (ADR-0014 Accepted 2026-07-08) |
| v10 (API & Web UI) | ✅ 完成 (ADR-0015 Accepted 2026-07-10) |
| **v11 (Multi-Dataset + Experiment History)** | ✅ **完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted 2026-07-25**（DoD #1-4 全绿）|
| **v12 (Python API & SDK Foundation)** | ✅ **完成** — DoD #1 SDK / #2 Async queue / #3 Registry 版本化+标签查询 全绿，ADR-0017 Accepted；PR #60 已交付（OPEN / CLEAN / MERGEABLE，CI 6/6 SUCCESS），待皇上 Merge |
| **v13 (Experiment Provenance & Reproducibility)** | 🟢 **DoD #1-#8 + #12-#16 全部完成** — #1 provenance capture（PR #61 待 Merge）/ #2 replay execution / #3 coverage dashboard / #4 content-addressed storage（PR #62 待 Merge）/ #5 artifact compatibility（v122 晚场交付）/ **#12 replay integrity guard（PR #63 待 Merge）** / **#7 CI 触发覆盖闭合（PR #66 待 Merge）** / **#8 PR 级 CI 覆盖验证（PR #67 待 Merge）** / **#14 CI 审计器环境无关性（PR #67 同批）** / **#16 CI 门禁强度单调性（PR #67 同批）**；ADR-0018 待 Accepted |
| **本轮 PR** | 🟢 **stack 拓扑缺陷已修复**（v131 晚场）：PR #66 head = `e3d5626`、PR #67 head = `833bcf6`（均已 push + 远端回读校验）；**`stack_topology_audit --strict` exit 0 — 5/5 links linear**；6 个 PR 全部 MERGEABLE/CLEAN、CI 全绿，**待皇上自底向上 Merge** |
| **stack 拓扑** | ✅ **已修复** — PR #63/#66 的 `diverged-duplicate`（同一 CI trigger 修复被两条分支各提交一次，内容逐字节相同）已消除；**`stack_topology_audit.py --strict` exit 0，5/5 links linear，0 repairable，0 blocked**；6 个 PR 现可自底向上无冲突合并 |
| **v13 DoD #18** | ✅ **Job dependency graph audit 完成** — `scripts/job_graph_audit.py` 可执行门禁 + hermetic 测试 62 条 + **CI 集成：`job-graph-audit` job 已加入 `pr-coverage-gate.needs`** |
| **CI 触发覆盖** | ✅ **已闭合** — `pull_request` 无 `branches:` 过滤器；`scripts/ci_trigger_audit.py` 门禁（exit 0/1）+ CI `ci-trigger-audit` 自举 job |
| **PR 级 CI 覆盖** | ✅ **已闭合** — `scripts/pr_coverage_audit.py` 门禁（exit 0/1）+ CI `pr-coverage-audit` 自举 job；**6/6 PR verified** |
| **门禁模式单调性** | ✅ **已闭合** — 两种模式共用唯一判定函数 `evaluate_gate()`；`--require-checks` 要求集合是默认的**严格超集**（+`checks_completed`）；新增独立 CI job `pr-coverage-gate`（`needs:` 全部 8 job + `pull_request` 事件守卫）|
| **CI 审计器环境无关性** | ✅ **已闭合** — head 分支 workflow 改为从 **GitHub Contents API** 读取（本地 git 降级为 fallback）；hermetic 测试；CI runner 上 `pr-coverage-audit` job **SUCCESS** |
| **Stack 拓扑审计** | ✅ **已闭合** — `scripts/stack_topology_audit.py` 审计 stacked PR 的 **shape**（ancestry / mergeability / duplicate payload）；默认门禁（`mergeable` + `no_duplicate_payload`）与严格门禁（+ `linear`）共用 `evaluate_gate()`，严格集合是默认集合的严格超集；**32 条 hermetic 测试**；**93 条全量审计测试**；**live audit 正确检出 PR #63/#66 分叉重复提交**；**底部向上 6/6 PR 合并零冲突** |
| **待合 PR #67** | 🟢 **PR #67 OPEN + CLEAN + MERGEABLE + CI 10/10 SUCCESS**（v13 DoD #8 + #14 + #16 + **#17 + #18**，head 已重放为 `833bcf6`，含 `job-graph-audit`）|
| **待合 PR #66** | 🟢 **PR #66 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #7，**head 已重放为 `e3d5626`**，与 #63 的重复提交已消除）|
| **待合 PR #63** | 🟢 **PR #63 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #4 + #6，待皇上 Merge）✅ **已通过回移修复获得首次 CI 验证**|
| **待合 PR #62** | 🟢 **PR #62 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #2-#4，待皇上 Merge）|
| **待合 PR #61** | 🟢 **PR #61 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #1 provenance capture，待皇上 Merge）|
| **待合 PR #60** | 🟢 **PR #60 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v12 三 DoD，待皇上 Merge）|
| **本轮分支** | `feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）|
| **v13 DoD #17** | ✅ **Stack topology audit 完成 + CI 修复** — `scripts/stack_topology_audit.py` 可执行门禁 + hermetic 测试 32 条 + **关键发现：`git merge-tree` 的退出码不是冲突信号**（第一版信任退出码 → 假阴性，已改为从输出解析）+ **CI 修复：3 条 CLI 测试改为 hermetic（fake gh），消除对 `GH_TOKEN` 的隐式依赖** |
| **v13 DoD #18** | ✅ **Job dependency graph audit 完成并落地** — `scripts/job_graph_audit.py` 可执行门禁 + hermetic 测试 62 条 + **三个具体缺陷：dangling `needs:` / `needs:` cycle / ungated verification job** + **CI 集成：`job-graph-audit` job 已加入 `pr-coverage-gate.needs`** + **CI 实测 10/10 SUCCESS（含 `pr-coverage-gate`）** |
| **v13 DoD #6** | ✅ **复现指南文档化完成** — `docs/REPRODUCE.md` v0.1→v1.0，ADR-0018 下轮待办第 2 条已闭合|
| **CI 安全审计** | ✅ **master 已脱险**：PR #58/#59 merged 后 master = pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0） |

---

## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 未来的每一个贡献者
- **v131 晚场价值（本轮）**：
  1. **修好了「看起来只差点一下 Merge、实际有一个 PR 不可按建议顺序合并」这个缺陷** —— 6 个 PR 全部 CLEAN 全部 CI 全绿，唯独 #63/#66 的 head 分支**各自独立提交了同一个 CI trigger 修复**，按建议顺序合并会产生重复提交
  2. **证明「audit 自己报的缺陷，可以用 audit 自己给的方案修好」** —— 修复后 `stack_topology_audit --strict` 从 exit 1 变 exit 0，不是绕过门禁，是修好了门禁要抓的缺陷
  3. **把「完成」推到「可交付」的最后一环** —— v13 全部 DoD 已完成，但 master HEAD 仍在 `4082158`；本轮让 6 个 PR 全部达到「可安全合并」状态，**v13 收口只差皇上点合并**
  4. **沉淀了三个可复用的踩坑修法**：rebase 的 **committer 邮箱**才是 GH007 的真凶（author 干净也没用）；`--force-with-lease` 的期望值**必须现读**（我以为 `f004255` 实际 `36a6dd3`）；**审计器解析裸分支名时，push 成功 ≠ 审计器能看见**（本地 ref 不同步会让 audit 对着旧 ref 报旧缺陷）
- **价值**：
  1. 修复了**「严格门禁比默认门禁更宽松」**这个反直觉的缺陷 —— 之前一个 CI 从不会为它触发的 PR，能靠陈旧 checks 从「严格」门禁里溜过去
  2. 把门禁判定**收敛到唯一一个函数**，单调性由**构造**保证（严格集合 = 默认集合的超集），不再依赖两段代码「碰巧」写对
  3. 区分了**「有 check」和「check 跑完了」**（`observed_checks` vs `completed_checks`）—— GitHub 在 workflow 开始时就创建 check run，之前这两件事被混为一谈
  4. **挖出并清除了上一轮的同义反复测试** —— 那类测试测的是自己、且在保护 bug；新测试全部调用真实代码路径，并用 **bug 注入验证过确实咬得住**
  5. 门禁接进 CI 时**没有引入新的 flaky 源** —— 用独立 job + `needs:` 显式排序 + `pull_request` 事件守卫，而不是把「等所有 checks 跑完」塞进并行 job 里
  6. **补上了三个已有审计都看不见的「形状」维度** —— stacked PR 的 ancestry / mergeability / duplicate payload；PR #63 与 PR #66 的分叉重复提交被检出
  7. **发现并修复了「`git merge-tree` 的退出码不是冲突信号」这个陷阱** —— 第一版信任退出码 → 假阴性，正好漏掉了它要抓的缺陷；已改为从输出解析
  8. **默认分支检测不硬编码** —— 三级检测（`gh repo view` / `git symbolic-ref` / fallback），防止对 `main` 仓库报空 stack
   9. **测试 hermeticity 审计** —— 发现并修复了 3 条 CLI 测试对 `GH_TOKEN` 的隐式依赖（CI runner 上 `gh pr list` rc=4 → 假失败）；全部 32 条 `stack_topology_audit` 测试现在是完全 hermetic 的
- **验证**：
  - 本地 P0 ✅ compileall 0 + import smoke OK
  - 本地 P1 ✅ **32 passed**（`test_stack_topology_audit.py`，全部 hermetic throwaway repo）
  - 本地 P1 baseline ✅ **672 passed / 5 skipped / 1 pre-existing timeout**（`test_cli_health_runs` 在 base commit `5035430` 上同样失败，非本轮引入）
  - 本地全量审计测试 ✅ **93 passed**（`stack_topology_audit` + `pr_coverage_audit` + `ci_trigger_audit`）
  - 本地 Live audit ✅ `stack_topology_audit.py` exit 1（**正确**检出 PR #63/#66 分叉重复提交）
  - 本地 Bottom-up merge ✅ **6/6 PR 合并零冲突**（实测验证：stack 本身可合并，但拓扑不线性）
  - **bug 注入 ✅** 重新注入原 bug → 测试失败（新测试确实咬得住）
  - **YAML ✅** `ci.yml` 解析通过，9 个 job，`pr-coverage-gate.needs` 正确
- **当前状态**：🟢 **无外部阻塞** — v13 DoD #1-#18 全部交付且本地 P0–P1 全绿；**stack 拓扑缺陷已修复（5/5 links linear）**；待皇上按 **#60 → #61 → #62 → #63 → #66 → #67** 自底向上 Merge + 确认 ADR-0018 Accepted
- **最近一次验证**：2026-11-05 21:30 CST（v131 晚场，**stack topology --strict exit 0（5/5 links clean）**，P1 **155 passed**，live ci_trigger/job_graph exit 0，**CI #66 7/7 + #67 10/10 SUCCESS**，6/6 PR CLEAN）
- **master HEAD**：`4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**：`feat/v13-pr-coverage-audit` = `833bcf6`（base `feat/v13-ci-trigger-coverage` = `e3d5626`），两分支均已 push 并远端回读校验
- **阻塞**：无（PR #60 / #61 / #62 / #63 / #66 / #67 待 Merge；按 CHARTER 第 7 步「等 Merge（由人工/自动合并）」，合并权不在本代理，本轮只做修复不做合并）
- **⚠️ 价值已完全实现**：**三个已有审计都看不见的「形状」维度被补上了** —— 而且**第一个实现版本就漏掉了它要抓的缺陷**（信任 `git merge-tree` 退出码 → 假阴性）。一个审计如果对它要抓的缺陷报「一切正常」，它就不是审计，是**盖章**。
- **🔧 本轮额外价值**：**测试的 hermeticity 本身就是一种审计** —— 3 条 CLI 测试在 CI 中假失败，暴露了「测试在测环境而不是在测代码」这个更深层的问题。修复后，`stack_topology_audit` 的 32 条测试全部 hermetic，不再依赖 `gh` / `GH_TOKEN` / 网络 / 真实仓库状态。
- **🔧 下一轮额外价值（v129 晚场）**：**补上了四个已有审计都看不见的「作业依赖图」维度** —— DoD #7 问 workflow 触发、DoD #8 问 PR 覆盖、DoD #16 问门禁单调性、DoD #17 问 stack 形状，**没有一个问 workflow 内部的 `jobs:` 块是否健康**。dangling `needs:`（一个字符的拼写错误就能把绿色 CI 变成「什么都没验证」的 CI）、`needs:` cycle（job 静默永不运行）、ungated verification job（gate 报告「已验证」但实际未验证，与 DoD #16 缺陷同构）—— 三个缺陷都被检出。**DoD #16 的教训泛化了**：一个 gate 如果不对它要抓的缺陷报失败，它就不是 gate，是**橡皮章**。
