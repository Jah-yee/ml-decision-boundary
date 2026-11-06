# NEXT_ROUND_THEME.md — ml-decision-boundary v132 早场（v14 release pipeline 审计 + 首次发布必然失败缺陷已修复）

**更新时间：** 2026-11-06 09:43 CST / 2026-11-06 01:43 UTC
**版本：** v132 早场
**维护人：** 太子
**本轮 run log：** `strategy/runs/2026-11-06-0943.md`

---

## 🟢 v132 早场 状态：**v14 — Release Pipeline Audit 交付；全仓唯一有写权限的发布流水线从「首次发布必然 exit 128」修到「经审计且逻辑正确」**

### 本轮交付：v14 — 审计并修复 `release.yml`

| 交付物 | 内容 |
|--------|------|
| **选题依据** | 四个已有审计**都显式排除** `release.yml` —— 每个排除都是对的，但**叠加起来**让**全仓唯一持 `contents: write`、唯一产出对外发布物**的流水线**零审计覆盖**；且本仓 `git tag` = **0** → **发布路径从未执行过一次** |
| **`scripts/release_audit.py`** | **新**：自研 YAML 子集解析器（**不引入 PyYAML**）+ 6 项门禁 + `--strict` 超集 + JSON 输出 |
| **`tests/test_release_audit.py`** | **新**：**68 条** hermetic 测试（13 类，含 7 条 bug 注入） |
| **`release.yml` / `ci.yml`** | **修**：6 处缺陷全修 / **加**：`release-audit` job + 接入 `pr-coverage-gate.needs` |
| **run log** | `strategy/runs/2026-11-06-0943.md`（**新**，含全部推导与证据） |

### 6 个实测缺陷（非推测）

| # | 缺陷 | 实测证据 |
|---|------|---------|
| D1 | **首次发布必然失败** | `git describe --tags --abbrev=0 HEAD~1` → `fatal: No names found` rc=**128** |
| D2 | **锚定在父提交而非上一个 tag** | merge / 发版后有提交落地时 changelog 区间就是错的 |
| D3 | **changelog 按字节截断** | `head -c 5000` → `UnicodeDecodeError` 且 **rc=0** → 损坏静默入库 |
| D4 | **无 concurrency 守卫** | 并发推 tag → 竞态改 `CHANGELOG.md` → 丢更新 |
| D5 | **第三方 action 用可变 tag** | `action-gh-release@v2`、`git-auto-commit-action@v5` |
| D6 | **permissions / trigger 未约束** | `write-all` 授予全部 scope；非 tag 触发则每 commit 发一次 release |

### 修复要点（最重要的技术判断）

```bash
CURRENT_TAG=$(git tag --points-at HEAD | head -1)
PREV_TAG=$(git tag --sort=-v:refname | grep -v "^${CURRENT_TAG}$" | head -1 || true)
```

> ⚠️ **第一版修复是错的。** `git describe --tags --abbrev=0 2>/dev/null || echo ""`
> 确实不再 exit 128、**看着是对的**，但实测解析出的是**正在发布的那个 tag**（`v0.2.0`）而非上一个（`v0.1.0`）——
> **把「崩溃」换成了「changelog 永远为空」的静默错误，后者更糟，因为它不会告诉你。**
> 正解必须**排除当前 tag**。真建 git repo 实测三种场景全对（首发布→`""`、二发布→`v0.1.0`、三发布→`v0.2.0`），
> 且对「被 tag 的提交是 merge」「上次发版后还有提交落地」天然免疫。

D3 改按行截断｜D4 加 `concurrency`（`cancel-in-progress: false`——发版**不该**被新 tag 取消）｜
D5 钉**真实上游 SHA**（`git ls-remote` 取回；第一版编造的 SHA 被审计判 `not a sha` → **审计比我对**）｜
D6 已合规无需改。

### 审计器自身被抓出的 3 个真实 bug（已修）

| Bug | 根因 |
|-----|------|
| `actions/checkout@v4` 被判「not a sha」 | **重复定义 `_TAG_REF_RE`**：残留的 `^tags:` 版本**遮蔽**了正确的那条 |
| `concurrency_expr` 恒为空 | 只认 inline 值，不认 block 形式 |
| `workflow_dispatch:` 漏检 | `tags:` 块把 `on_event` 标记**覆盖**了 |

> 修第 3 个时「`indent <=` → `indent <`」这个一行改动让 **23 条测试挂掉**（「块在其 key 层级上的兄弟键」被误判出栈）。
> **正解是重写块模型，不是打补丁。最小改动 ≠ 最小风险。**

### 动手前的复核（不轻信上一轮的自我报告）

`spec/phases.md`：v0–v13 全部完成 ✅（ADR-0018 Accepted）｜`git tag`：**0 个** → 发布路径从未执行｜
PyYAML：**不在** `requirements.lock` → 不引入新依赖｜`spec/CHARTER.md` 第 7 步「等 Merge」→ **合并权不在本代理**

### 本轮的元观察

**「显式排除」是双刃的。** 四个审计排除 `release.yml` 每一个都是对的，
但**四个「对的」叠加起来**，让唯一有写权限的流水线零覆盖。
**审计覆盖面是整体属性，不能只看单个审计自己声明的范围。**

**崩溃的修复可能比崩溃更危险。** 它把「崩溃」换成了「静默错误」——
后者更糟，因为它不会告诉你。**能崩的缺陷是善意的：它会告诉你。**

**一个连自家第一方 action 都会误报的审计，是不能信任的。**
**测试比审计先发现，是因为测试断言的是「对的东西」而不是「审计现在说的东西」。**


## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-06 09:43** | 🟢 **v132 早场 #1：v14「Release Pipeline Audit」交付 —— 全仓唯一有写权限的发布流水线从「首次发布必然 exit 128」修到「经审计且逻辑正确」。** 🔍 **选题**：四个已有审计**都显式排除** `release.yml` —— 每个排除都对，但**叠加起来**让唯一持有 `contents: write`、唯一产出对外发布物的流水线**零覆盖**；且本仓 `git tag` = **0** → 发布路径**从未执行过**。💥 **6 缺陷全实测**：D1 `git describe --tags --abbrev=0 HEAD~1` → rc=**128**；D2 锚定父提交非 tag；D3 `head -c 5000` 劈开 UTF-8 且 **rc=0** → 损坏静默入库；D4 无 concurrency；D5 action 用可变 tag；D6 permissions/trigger 未约束。🛠 **最重要的判断**：第一版修法 `git describe --tags --abbrev=0 2>/dev/null` **看着对**但实测解析出的是**正在发布的那个 tag** → 把「崩溃」换成「changelog 永远为空」的**静默错误**（更糟，它不告诉你）。正解必须**排除当前 tag**：`git tag --points-at HEAD` + `grep -v` → 真建 repo 实测四种场景全对。D5 用 **`git ls-remote` 取回的真实上游 SHA**（编造的 SHA 被审计判 `not a sha` → **审计比我对**）。🐛 **审计器自身被抓 3 bug**（重复定义 `_TAG_REF_RE` 遮蔽正确实现 / `concurrency_expr` 只认 inline / `tags:` 覆盖 `on_event` 标记）；修第 3 个时「`indent <=`→`indent <`」一行改动让 **23 条测试挂掉** → **正解是重写块模型：最小改动 ≠ 最小风险**。✅ **验收**：`release_audit --strict` **exit 0（6/6）** + compileall ✅ + **P1 68 passed** + **bug 注入**（修好后 4 条检出断言**确实失败** = 检出是真的；另加 7 条 `TestBugInjection`）+ `job_graph_audit` **exit 0**（11 jobs，`release-audit` 正确识别为 gate 且已入 `pr-coverage-gate.needs`）。💡 **元观察**：**四个「对的」排除叠加起来**会让唯一高危面零覆盖——审计覆盖面是**整体属性**；**能崩的缺陷是善意的**。📌 **请皇上决策**：① 合并本轮 PR；② **#60→#61→#62→#63→#66→#67** 自底向上 Merge；③ 确认 ADR-0018 Accepted；④（可选）打第一个 tag 验证发布链路——会触发**真实发布**，建议等 PR 合并后。run log: `strategy/runs/2026-11-06-0943.md` 🟢 |
| **2026-11-05 21:30** | 🟢 **v131 晚场 #1：修复 v13 stack 的 `diverged-duplicate` 拓扑缺陷，6 个 PR 现在可自底向上安全合并。** PR #63/#66 重复提交已用 `cherry-pick` 重放消除（#66→`e3d5626`、#67→`833bcf6`）；`stack_topology_audit --strict` exit 0（5/5 links linear）；CI #66 7/7 + #67 10/10 SUCCESS。**请皇上自底向上 Merge #60→#61→#62→#63→#66→#67** + 确认 ADR-0018 Accepted。（正文见 archive）🟢* |
| **2026-11-04 21:30** | 🟢 **v129 晚场 #1：v13 DoD #18「Job Dependency Graph Audit」全部交付。** 新增 `scripts/job_graph_audit.py`（676 行纯 stdlib），检 dangling `needs:` / `needs:` cycle / ungated verification job 三个缺陷；门禁同构（严格集合 = 默认集合严格超集）；hermetic 测试 **62 条**；全量审计 **155 passed**；CI 新增 `job-graph-audit` job 并接入 `pr-coverage-gate.needs`；live `--strict` exit 0。（正文见 archive）🟢* |
| **2026-11-03 21:30** | 🟢 **v128 晚场 #1：v13 DoD #17 CI 修复完成。** 3 条 CLI 测试改为 hermetic（fake `gh`，不注入 `GH_TOKEN`）；CI run `41646891602` **9/9 SUCCESS**。（正文见 archive）🟢* |
| **2026-11-03 09:43** | 🟢 **v128 早场 #1：v13 DoD #17「Stack Topology Audit」全部交付。** 新增 `scripts/stack_topology_audit.py`（ancestry / mergeability / duplicate payload）；关键发现 `git merge-tree` 退出码不是冲突信号（改为解析输出）；hermetic 测试 **32 条**；全量审计 **93 passed**；bottom-up 合并 6/6 零冲突。（正文见 archive）🟢* |
| **2026-11-02 21:38** | 🟢 **v127 晚场 #1：v13 DoD #16「CI 门禁强度单调性」全部交付。**（详细正文见 archive）🟢* |
| **2026-11-01 21:38** | 🟢 **v126 晚场 #1：v13 DoD #14「CI 审计器环境无关性」全部交付 + PR #67 CI 8/8 SUCCESS。**（详细正文见 archive）🟢* |

## 当前全局状态

| 项目 | 状态 |
|------|------|
| **v0–v10** | ✅ 全部完成（ADR-0013/0014/0015 Accepted）|
| **v11 (Multi-Dataset + Experiment History)** | ✅ 完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted |
| **v12 (Python API & SDK Foundation)** | ✅ 完成 — ADR-0017 Accepted；PR #60 已交付（OPEN/CLEAN/CI 6/6 SUCCESS），待 Merge |
| **v13 (Experiment Provenance & Reproducibility)** | 🟢 DoD #1–#8 + #12–#18 全部完成 — #1 PR #61 / #4 PR #62 / #12 PR #63 / #7 PR #66 / #8+#14+#16+#17+#18 PR #67，**全部待 Merge**；ADR-0018 待 Accepted |
| **v14 (Release Pipeline Audit)** | 🟢 **DoD #1–#7 全部交付** — `scripts/release_audit.py`（自研 YAML 子集解析器，**不引入 PyYAML**）+ 6 项门禁 + `--strict` 严格超集 + `release.yml` **6 处缺陷全修** + **68 条 hermetic 测试**（13 类，含 7 条 bug 注入）+ **CI `release-audit` job 已入 `pr-coverage-gate.needs`** + `job_graph_audit --strict` exit 0（11 jobs）|
| **发布流水线状态** | ✅ **从「首次发布必然 exit 128」修到「经审计且逻辑正确」** — 正确解法是 `git tag --points-at HEAD` + `grep -v` **排除当前 tag**（单纯 `git describe --tags` 会解析出**正在发布的那个 tag**，把「崩溃」换成「changelog 永远为空」的**静默错误**）；真建 git repo 实测四种 tag 场景全对；第三方 action 已钉**真实上游 SHA** |
| **本轮 PR** | 🟢 **v14 Release Pipeline Audit**：`release_audit.py`（新）+ `test_release_audit.py`（新，68 条）+ `release.yml` 修复 + `ci.yml` 接入；**待皇上 Merge** |
| **v13 stack** | ✅ 拓扑缺陷已修复 — PR #63/#66 的 `diverged-duplicate` 已消除；**`stack_topology_audit --strict` exit 0，5/5 links linear**；6 个 PR 现可自底向上无冲突合并 |
| **待合 PR #67/#66/#63/#62/#61/#60** | 🟢 全部 **OPEN + CLEAN + MERGEABLE + CI 全绿**；#67 head = `833bcf6`、#66 head = `e3d5626`（已 push + 远端回读校验）|
| **CI 触发覆盖 / PR 级 CI 覆盖** | ✅ 已闭合 — `ci_trigger_audit` / `pr_coverage_audit` 门禁 + 自举 CI job；**6/6 PR verified** |
| **门禁模式单调性 / CI 审计器环境无关性** | ✅ 已闭合 — 两模式共用唯一判定函数 `evaluate_gate()`，严格集合是默认集合**严格超集**；审计器已脱离 `GH_TOKEN` 隐式依赖 |
| **CI 安全审计** | ✅ **master 已脱险**：pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（63 CVE → 0）|


## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 所有会读到 CHANGELOG 的使用者 / 未来的每一个贡献者
- **v132 早场价值（本轮）**：
  1. **补上了「四个已有审计都不看的那个唯一高危面」** —— `release.yml` 是全仓唯一持 `contents: write`、唯一产出对外发布物的流水线，却因四个审计**各自都正确地**排除它而**零覆盖**；且本仓**从未打过 tag**，它第一步**必然 exit 128**——此前无人知道
  2. **修好了「首次发布必然失败」** —— 0 成本、100% 触发的缺陷，修复后首次发布也能走完
  3. **识别并避开了「比崩溃更危险的静默错误」** —— `git describe --tags` 会解析出**正在发布的那个 tag**，让每次发版后的 changelog 永远为空**且不报错**；正解必须**排除当前 tag**，并**真建 git repo 实测四种场景**
  4. **审计器自身被抓出 3 个真实 bug 并全修** —— 含一个**重复定义 `_TAG_REF_RE` 遮蔽正确实现**的隐蔽 bug（致 `actions/checkout@v4` 被误判「not a sha」）
  5. **证明「bug 注入」是唯一能证明门禁不是橡皮章的手段** —— 修好后 4 条检出断言**确实失败**（检出是真的），随即改写为「断言已修复」并新增 **7 条 `TestBugInjection`**
  6. **修掉了「损坏静默入库」** —— `head -c 5000` 会劈开 UTF-8 字符，而 **rc=0** 意味着损坏文件被无声提交进 master；改为按行截断
  7. **把第三方 action 钉到真实上游 SHA** —— 且是**被审计逼出来的**（编造的 SHA 直接被判 `not a sha`）
  8. **证明「最小改动 ≠ 最小风险」** —— 一行改动让 **23 条测试挂掉**；正解是**重写块模型**
  9. **接进 CI 且不引入新缺陷** —— `release-audit` 已列入 `pr-coverage-gate.needs`，`job_graph_audit` exit 0（11 jobs）

- **v132 早场价值边界（诚实降级，不夸大）**：
  - 本轮交付的是**「发布路径从「必然失败」变成「经过审计且逻辑正确」」**，**不是**「发布已经成功」
  - **端到端发布尚未验证** —— 需要一个真实 tag 才能验证，而打 tag 触发真实发布**属于需皇上决策的动作**，本代理不擅自执行
  - **合并权归皇上**（`spec/CHARTER.md` 第 7 步），本轮只交付不合并
- **v131 晚场价值（上轮）**：修好了「6 个 PR 全绿却有一个不可按建议顺序合并」；证明「audit 自己报的缺陷可以用 audit 自己给的方案修好」；把 v13 从「DoD 完成」推到「可安全合并」。（正文见 archive）
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
