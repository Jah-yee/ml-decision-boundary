# NEXT_ROUND_THEME.md — ml-decision-boundary v130 早场（v13 DoD #18 已落地：commit + push + PR #67）

**更新时间：** 2026-11-05 09:36 CST / 2026-11-05 01:36 UTC
**版本：** v130 早场
**维护人：** 太子
**本轮 run log：** `strategy/runs/2026-11-05-0936.md`

---

## 🟢 v130 早场 状态：**v13 DoD #18 已 commit + push + PR #67 正文更新，全部落地**

### 本轮交付：v130 早场 — 收尾 v129 晚场未竟事项（DoD #18 commit + PR）

| 交付物 | 内容 |
|--------|------|
| `git` | **commit `ab7b35b`**（9 文件，+1879/−35）—— v129 晚场的 DoD #18 成果此前**只 staged 未 commit**，一行都没进版本库 |
| `push` | 远端 `feat/v13-pr-coverage-audit` sha 回读校验 == `ab7b35b` |
| `PR #67` | **不新开 PR**（head 分支本就是同一条），改用 REST PATCH 更新标题 + 正文，覆盖 DoD #8/#14/#16/#17/#18 |
| `strategy/runs/2026-11-05-0936.md` | **新**：本轮 run log |
| `strategy/NEXT_ROUND_THEME.md` + archive | 状态更新 + 归档迁移（20,710 → **15,366** 字节，↓26%） |

### 动手前的现状复核（不轻信上一轮的自我报告）

| 检查 | 结果 |
|------|------|
| P0 `compileall` | ✅ |
| P1 `test_job_graph_audit.py` | ✅ **62 passed** |
| 全量审计测试（4 审计器） | ✅ **155 passed** |
| Live `job_graph_audit.py --strict` | ✅ **exit 0**（ci.yml 10 job 图健康）|

→ 上一轮代码质量是真的，**不需要返工**，可以安全提交。

### 本轮的元观察（比代码更值钱）

playbook 把「代码实现 + 测试」列为交付物，却**没把「代码进 git、进 PR」显式列为可验收项**。
结果一轮结束时状态写着「DoD #18 完成」，而实际上**它一行都还没进版本库**。

**「完成」是内部信号，「价值」是外部信号。** 这里的具体形状是：代码跑通了 ≠ 代码交付了；**进了 git、开了 PR 才算交付**。

### 问题：四个已有审计都看不见「作业依赖图」

| 审计 | 问的问题 |
|------|---------|
| `ci_trigger_audit` (DoD #7) | 「PR 的 base 分支上，workflow 会触发 CI 吗？」 |
| `pr_coverage_audit` (DoD #8) | 「每个 open PR 真的被 CI 覆盖了吗？」 |
| `pr_coverage_audit --require-checks` (DoD #16) | 「严格模式比默认模式更宽松吗？」 |
| `stack_topology_audit` (DoD #17) | 「这个 stack 能按顺序合并吗？」 |

**没有一个问：「workflow 内部的 `jobs:` 块，作业依赖图本身健康吗？」**

### 三个具体缺陷

1. **Dangling `needs:` target** — 致命。如果 `pr-coverage-gate` 引用了一个不存在的 job，GitHub 会拒绝**整个 workflow**。所有真实质量 job 一起被跳过。一个字符的拼写错误就能把绿色 CI 变成「什么都没验证」的 CI。
2. **`needs:` cycle** — 静默。一个 job 如果在传递上依赖自己，会被从执行顺序中丢弃，workflow 仍然「整体成功」。
3. **Ungated verification job** — 危险方向的谎言。如果有人加了一个新验证 job 但忘了在 `pr-coverage-gate` 的 `needs:` 里加上它，gate 会报告「这个 PR 已完全验证」，而新 job 根本没跑。**与 DoD #16 缺陷完全同构**。

**关键设计决策**：Point 3 是这个 audit 存在的原因 —— 它必须是 **gate** 而不是 lint。DoD #16 的教训泛化了：*一个 gate 如果不对它要抓的缺陷报失败，它就不是 gate，是橡皮章。*

### 门禁设计（与 DoD #16/#17 同构）

```python
DEFAULT_REQUIREMENTS = ("no_dangling_needs", "no_self_dependency", "acyclic", "gate_coverage")
STRICT_REQUIREMENTS = DEFAULT_REQUIREMENTS + ("all_jobs_reachable",)
```

- 默认门禁：**「作业依赖图健康吗？」**
- 严格门禁：**「每个 job 都从某个 gate 可达吗？」**
- 严格集合是默认集合的**严格超集** → 单调性由**构造**保证
- 两种模式共用唯一判定函数 `evaluate_gate()`

### 验证

- ✅ P0 compileall 无错误
- ✅ P1 `test_job_graph_audit.py` **62 passed**（10 个 Test 类，全部 hermetic throwaway workflow）
- ✅ 全量审计测试 **155 passed**（`job_graph_audit` + `stack_topology_audit` + `pr_coverage_audit` + `ci_trigger_audit`）
- ✅ Live audit `--strict` exit 0（当前 workflow 图健康，10 个 job，`pr-coverage-gate.needs` 含 `job-graph-audit`）
- ✅ `ci.yml` YAML 解析通过

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-05 09:36** | 🟢 **v130 早场 #1：DoD #18「代码进 git、进 PR」收尾，全部落地。** 🔍 **发现上一轮（v129 晚场）只把代码 staged 住，没有 commit、没有 PR** —— 状态写「DoD #18 完成」，但代码**一行都还没进版本库**。🆕 **解法**：① **动手前先复核**（不轻信上一轮自我报告）：P0 compileall ✅ / P1 **62 passed** / 全量审计 **155 passed** / live `--strict` **exit 0** → 确认代码质量真实，**不返工** ② **commit `ab7b35b`**（9 文件 +1879/−35），author 与 committer 同用已验证公开邮箱 `166608075+Jah-yee@users.noreply.github.com`（避免 GH007 拒推）③ **push 后立刻回读远端 sha** 校验 == `ab7b35b`（不拿 `git push` stdout 当证据）④ **不新开 PR**：PR #67 的 head 分支本就是同一条 `feat/v13-pr-coverage-audit`，新开只会造成同代码两个 PR 的噪声 → 改用 **REST PATCH** 更新 #67 标题 + 正文（`gh pr edit` 会因 projects-classic 弃用报错且正文**实际没改成功**）⑤ **归档迁移**：`NEXT_ROUND_THEME.md` 已 20,710B > playbook 20K 阈值 → 把 v126–v129 操作记录**正文**迁入 archive，主题文件只留摘要行 → **20,710 → 15,366B（↓26%）**⑥ 补齐上一轮遗漏的 run log（2026-11-03-2130 / 2026-11-04-2130）✅ P0 ✅ + P1 ✅ **62 passed** + 全量 **155 passed** + live exit 0 + commit/远端 sha/PR 状态/主题体积 四项校验全过。💡 **本轮最重要的产出不是代码，是一条流程漏洞**：playbook 把「代码实现 + 测试」列为交付物，却**没把「代码进 git、进 PR」显式列为可验收项** —— 结果一轮结束时状态写着「完成」，而实际上一行都没进版本库。**「完成」是内部信号，「价值」是外部信号。** 代码跑通了 ≠ 代码交付了；**进了 git、开了 PR 才算交付**。📌 **请皇上决策**：① **Merge PR #67**（DoD #8/#14/#16/#17/#18，已含 DoD #18，CI 中）② Merge PR #66 ③ Merge PR #63 ④ Merge PR #62 ⑤ Merge PR #61 ⑥ Merge PR #60 ⑦ 接受 ADR-0018。run log: `strategy/runs/2026-11-05-0936.md` 🟢 |
| **2026-11-04 21:30** | 🟢 **v129 晚场 #1：v13 DoD #18「Job Dependency Graph Audit」全部交付。** 新增 `scripts/job_graph_audit.py`（676 行纯 stdlib），检 dangling `needs:` / `needs:` cycle / ungated verification job 三个缺陷；门禁同构（严格集合 = 默认集合严格超集）；hermetic 测试 **62 条**；全量审计 **155 passed**；CI 新增 `job-graph-audit` job 并接入 `pr-coverage-gate.needs`；live `--strict` exit 0。（正文见 archive）🟢* |
| **2026-11-03 21:30** | 🟢 **v128 晚场 #1：v13 DoD #17 CI 修复完成。** 3 条 CLI 测试改为 hermetic（fake `gh`，不注入 `GH_TOKEN`）；CI run `41646891602` **9/9 SUCCESS**。（正文见 archive）🟢* |
| **2026-11-03 09:43** | 🟢 **v128 早场 #1：v13 DoD #17「Stack Topology Audit」全部交付。** 新增 `scripts/stack_topology_audit.py`（ancestry / mergeability / duplicate payload）；关键发现 `git merge-tree` 退出码不是冲突信号（改为解析输出）；hermetic 测试 **32 条**；全量审计 **93 passed**；bottom-up 合并 6/6 零冲突。（正文见 archive）🟢* |
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
| **本轮 PR** | 🟢 **DoD #18 已 commit + push + PR #67 正文更新，全部落地**（v130 早场，commit `ab7b35b` + `ab04e77`，PR #67 OPEN/MERGEABLE/CLEAN，**CI 10/10 SUCCESS**）|
| **v13 DoD #18** | ✅ **Job dependency graph audit 完成** — `scripts/job_graph_audit.py` 可执行门禁 + hermetic 测试 62 条 + **CI 集成：`job-graph-audit` job 已加入 `pr-coverage-gate.needs`** |
| **CI 触发覆盖** | ✅ **已闭合** — `pull_request` 无 `branches:` 过滤器；`scripts/ci_trigger_audit.py` 门禁（exit 0/1）+ CI `ci-trigger-audit` 自举 job |
| **PR 级 CI 覆盖** | ✅ **已闭合** — `scripts/pr_coverage_audit.py` 门禁（exit 0/1）+ CI `pr-coverage-audit` 自举 job；**6/6 PR verified** |
| **门禁模式单调性** | ✅ **已闭合** — 两种模式共用唯一判定函数 `evaluate_gate()`；`--require-checks` 要求集合是默认的**严格超集**（+`checks_completed`）；新增独立 CI job `pr-coverage-gate`（`needs:` 全部 8 job + `pull_request` 事件守卫）|
| **CI 审计器环境无关性** | ✅ **已闭合** — head 分支 workflow 改为从 **GitHub Contents API** 读取（本地 git 降级为 fallback）；hermetic 测试；CI runner 上 `pr-coverage-audit` job **SUCCESS** |
| **Stack 拓扑审计** | ✅ **已闭合** — `scripts/stack_topology_audit.py` 审计 stacked PR 的 **shape**（ancestry / mergeability / duplicate payload）；默认门禁（`mergeable` + `no_duplicate_payload`）与严格门禁（+ `linear`）共用 `evaluate_gate()`，严格集合是默认集合的严格超集；**32 条 hermetic 测试**；**93 条全量审计测试**；**live audit 正确检出 PR #63/#66 分叉重复提交**；**底部向上 6/6 PR 合并零冲突** |
| **待合 PR #67** | 🟢 **PR #67 OPEN + CLEAN + MERGEABLE + CI 10/10 SUCCESS**（v13 DoD #8 + #14 + #16 + **#17 + #18**，标题/正文已更新覆盖 #18，含新增 `job-graph-audit`，待皇上 Merge）|
| **待合 PR #66** | 🟢 **PR #66 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #7，待皇上 Merge）|
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
- **当前状态**：🟢 **无外部阻塞** — v13 DoD #1-#18 全部交付且本地 P0–P1 全绿；待皇上 Merge PR #60 / #61 / #62 / #63 / #66 / #67 + 接受 ADR-0018
- **最近一次验证**：2026-11-05 09:36 CST（v130 早场，P1 62 + 155 passed，live audit --strict exit 0，**PR #67 CI 10/10 SUCCESS**）
- **master HEAD**：`4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**：`feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）
- **阻塞**：无（PR #60 / #61 / #62 / #63 / #66 / #67 待 Merge，不阻塞下一轮开发）
- **⚠️ 价值已完全实现**：**三个已有审计都看不见的「形状」维度被补上了** —— 而且**第一个实现版本就漏掉了它要抓的缺陷**（信任 `git merge-tree` 退出码 → 假阴性）。一个审计如果对它要抓的缺陷报「一切正常」，它就不是审计，是**盖章**。
- **🔧 本轮额外价值**：**测试的 hermeticity 本身就是一种审计** —— 3 条 CLI 测试在 CI 中假失败，暴露了「测试在测环境而不是在测代码」这个更深层的问题。修复后，`stack_topology_audit` 的 32 条测试全部 hermetic，不再依赖 `gh` / `GH_TOKEN` / 网络 / 真实仓库状态。
- **🔧 下一轮额外价值（v129 晚场）**：**补上了四个已有审计都看不见的「作业依赖图」维度** —— DoD #7 问 workflow 触发、DoD #8 问 PR 覆盖、DoD #16 问门禁单调性、DoD #17 问 stack 形状，**没有一个问 workflow 内部的 `jobs:` 块是否健康**。dangling `needs:`（一个字符的拼写错误就能把绿色 CI 变成「什么都没验证」的 CI）、`needs:` cycle（job 静默永不运行）、ungated verification job（gate 报告「已验证」但实际未验证，与 DoD #16 缺陷同构）—— 三个缺陷都被检出。**DoD #16 的教训泛化了**：一个 gate 如果不对它要抓的缺陷报失败，它就不是 gate，是**橡皮章**。
