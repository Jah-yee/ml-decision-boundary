# NEXT_ROUND_THEME.md — ml-decision-boundary v134 早场（审计覆盖率审计：审计 job 跑了，但没覆盖它声称守护的产物）

**更新时间：** 2026-11-07 09:38 CST / 2026-11-07 01:38 UTC
**版本：** v134 早场
**维护人：** 太子
**本轮 run log：** `strategy/runs/2026-11-07-0938.md`

---

## 🟢 v134 早场 状态：**新增元审计 `audit_coverage_audit.py` —— 审计「审计到底看了哪些产物」；实测证明 v133 刚修的 `ci.yml` 权限缺陷此前删掉就绿**

### 本轮交付：闭合整个缺陷类（不只改一行调用）

| 交付物 | 内容 |
|--------|------|
| **选题依据** | v133 刚修好的 `ci.yml` 缺 `permissions:` 缺陷 —— **删掉它，CI 仍然全绿**。实测注入缺陷后，`release_audit --workflow release.yml --strict` / `ci_trigger_audit` / `job_graph_audit` **全部 exit 0**；而把同一文件**直接**交给审计器 → **exit 1**，报 `permissions_explicit` 失败。**审计器没毛病，是调用方把它指错了地方。** |
| **`scripts/audit_coverage_audit.py`** | **新增**（纯 stdlib，自写 YAML 子集解析器）：审计**审计器** —— 算出每次审计调用实际覆盖的 workflow 集合，检测 ①`coverage_narrowed`（显式收窄且是严格子集）②`workflow_uncovered`（完全未覆盖） |
| **`.github/workflows/ci.yml`** | **改**：`release-audit` 调用去掉 `--workflow` 收窄，改为默认 glob（覆盖全部 2 个 workflow）；**新增 `audit-coverage-audit` job** 并接入 `pr-coverage-gate.needs` |
| **`tests/test_audit_coverage_audit.py`** | **新增 32 条** hermetic 测试：解析器（`run: \|` 块标量 / `- name:` 形态 / 注释剥离 / dedent 结束）/ 调用发现 / 两项检测 / 门禁单调性 / CLI / **bug 注入** / 真实仓库不变量 |
| **run log** | `strategy/runs/2026-11-07-0938.md`（新，含全部推导与证据） |
| **PR** | 待建（分支 `feat/v14-audit-coverage-audit`，叠在 `feat/v14-release-audit` 之上） |

### 核心修复：把「收窄」本身变成缺陷

- **v133 晚场的教训是「误报是有害的」** → 本轮延续：**窄而准**，只审**确实审计 workflow 文件**的脚本
- `pr_coverage_audit.py` **故意不在受审名单** —— 它审的是「PR」不是「workflow 文件」，对它而言 `--workflow` 不构成覆盖率收窄；列入即假阳性
- **门禁单调性由构造保证**：两模式共用唯一判定函数 `evaluate_gate()`，strict 要求集是 default 的严格超集
- **strict 的一个语义澄清**：strict 禁止**任何**收窄，即使该收窄恰好覆盖全部文件 → 判定必须**从 invocations 读**，不能只从 problems 读（已用测试焊死）

### 解析器的两次真实 bug（都是自己抓到的）

1. **`- run: <cmd>` 解析不到** —— 正则 `(?:\s+-|\s+)run:` 里 `-` 与 `run:` 之间的空格没被吃掉
2. **`run: |` 块标量解析不到** —— 块体行（indent 10）会先命中「普通 step」分支（`indent >= 6`）并被 `continue` 吃掉，**永远到不了**块体分支 → 必须前置

> 第 2 条值得单独说：**本仓每一个多行 CI step 都是 `run: |` 写的**。一个只会读 `- run: <单行>` 的解析器，在本仓会找到 **0 个**审计调用 —— 而且它**不会报错**，只会安静地说「所有 workflow 都未被覆盖」。**静默降级比崩溃危险。**

### 元观察（本轮最值钱的一条）

**「有 CI 证据」和「CI 证据有效」是两件事。**

上一轮的主题文档白纸黑字写着「`release_audit --strict` exit 0（6/6）」—— **看起来是好消息**。实际上 CI job 传的是 `--workflow release.yml`，**恰好**绕开了唯一的 bug。

> **CI 是「执行者」的证据，不是「设计者」的证据。** 一个从没指向正确目标的检查，跑得再绿也是**零信息** —— 甚至更糟：它把「未检查」伪装成「已检查」。

**覆盖率是整体属性，不可能靠逐个调用点自觉维护** —— 这和 v132 晚场「四个『对的』排除叠加起来」是同一个形状的第二次出现（那次是四个排除，这次是一个收窄参数）。所以解法也不能是逐个自觉，必须是**一个机器检查**。

### 一个结构性的观察：审计器也要被审计

本仓已有 6 个审计器都在审「产物」；现在多了一个审「审计器」。

> 后者问的问题和前者**在结构上不同**：其他审计问「这个产物对吗」，它问「**这个审计真的看了它说要看的东西吗**」。

后者是前者的**前提**。一个收窄的审计器会把真缺陷变成「已检查」的假象 —— **它污染的不是自己的输出，而是其他所有审计的可信度**。

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-07 09:38** | 🟢 **v134 早场 #1：新增元审计 `audit_coverage_audit.py` —— 审计「审计到底看了哪些产物」；实测证明 v133 刚修的 `ci.yml` 权限缺陷此前删掉就绿。** 🔍 **选题**：上一轮刚修好的 `ci.yml` 缺 `permissions:` 缺陷 —— **删掉它，CI 仍然全绿**。实测：注入该缺陷后 `release_audit --workflow release.yml --strict` / `ci_trigger_audit` / `job_graph_audit` **全部 exit 0**；而把同一文件**直接**交给审计器 → **exit 1**，报 `permissions_explicit` 失败。💥 **根因**：`ci.yml` 的 `release-audit` job 传了 `--workflow .github/workflows/release.yml`，把审计**收窄到单文件**（本仓有 2 个 workflow）→ **审计器没毛病，是调用方把它指错了地方**。🛠 **修法**：不只改一行调用，而是新增**元审计**闭合整个缺陷类 —— 算出每次审计调用实际覆盖的 workflow 集合，检测 ①`coverage_narrowed`（显式收窄且是严格子集）②`workflow_uncovered`（完全未覆盖）；同时把 `ci.yml` 调用改为默认 glob，并新增 `audit-coverage-audit` job 接入 `pr-coverage-gate.needs`。💡 **误报控制（延续上轮）**：`pr_coverage_audit.py` **故意不在受审名单** —— 它审的是「PR」不是「workflow 文件」，列入即假阳性；**窄而准**。🐛 **解析器两次真实 bug（自抓）**：①`- run:` 正则漏掉 `-` 与 `run:` 之间的空格；②`run: |` **块体行会先命中「普通 step」分支被 `continue` 吃掉**，永远到不了块体分支 → 必须前置（**本仓每个多行 CI step 都是 `run: |` 写的**，只会读单行的解析器在本仓会找到 **0 个**调用且**不报错** —— 静默降级比崩溃危险）。🧪 **测试 32 条**（解析器含块标量 / 两种 step 形态 / 注释剥离 / dedent 结束 / 两项检测 / 单调性 / CLI / bug 注入 / 真实仓库不变量）。✅ **验收**：P0 compileall exit 0；P1 本轮 **32 passed** / **全量 899 passed + 5 skipped**（baseline 867 → +32）；live `audit_coverage_audit --strict` **exit 0**；`release_audit --strict` / `job_graph_audit --strict` / `ci_trigger_audit` 全 exit 0。🐛 **回归证明**：重新收窄 → 新审计 **exit 1**（`coverage_narrowed` + `no_narrowed_invocations` 双失败）= 守卫生效。💡 **元观察**：**「有 CI 证据」和「CI 证据有效」是两件事** —— 上一轮文档里的「exit 0」实际**恰好**绕开了唯一的 bug；**CI 是执行者的证据，不是设计者的证据**，一个没指向正确目标的检查跑得再绿也是**零信息**，甚至更糟：它把「未检查」伪装成「已检查」。📌 **请皇上决策**：① 合并本轮 PR；② **#60→#61→#62→#63→#66→#67→#68→本轮** 自底向上 Merge；③ 确认 ADR-0018 Accepted。run log: `strategy/runs/2026-11-07-0938.md` 🟢 |
| **2026-11-06 21:30** | 🟢 **v133 晚场 #1：修 v14 审计器自身的 bug + kind 分级 + 修 `ci.yml` 缺 `permissions:` 的真实缺陷。** 🔍 **选题**：上一轮 theme 自述「`release_audit --strict` exit 0（6/6）」——**实测 exit 1**。上一轮大概率跑的是 `--workflow release.yml`（**单文件**），而**默认 glob**（带上 `ci.yml`）是坏的。**验收命令的写法，决定了验收是否有效**；一个只验「我指定的那条路径」的验收，和**没验**信息量上几乎没有区别。💥 **根因**：审计器把**发布专用门禁**施加到 `ci.yml`——4 项误报（CI 不需要 tag 发现/changelog/concurrency）+ 1 项**语义反转**（`trigger_safe` 对 release 是「必须有 tags: 过滤」，对 CI 是「**不得**只由 tag 触发」）。🛠 **修法**：`classify_workflow()` 按语义分类（`tags:` 过滤 / 名称含 release / 持 `contents: write`）+ 要求集按 kind 分组 + `evaluate_gate()` kind 感知；**对每种 kind，strict 是 default 的严格超集**（由构造保证）。🎯 **修好后才暴露的真缺陷**：`ci.yml` **完全没有 `permissions:` 块** → CI 的 `GITHUB_TOKEN` 继承仓库默认权限（多为 read-write），**而没有任何 CI job 需要写** → 已补 `contents: read` / `pull-requests: read`。💡 **元观察**：**误报不只是噪音，误报是有害的**——6 项全挂时没人分辨哪几颗是真的，真缺陷被淹没；修好后只剩 1 项红，**而那一项是真的**。**CI 绿 ≠ 工具对**——CI job 恰好显式传了单文件，**恰好**绕开了唯一的 bug，所以上一轮**有** CI 证据而那个证据**无效**。🧪 **测试 68 → 100**（6 类新增，含默认 glob 路径 + 跨 kind 单调性 + bug 注入）。✅ **验收**：P0 compileall exit 0；P1 本轮 **100 passed**；**全量 867 passed / 5 skipped**（baseline 672 → +195）；**live `release_audit --strict`（默认 glob）exit 0**；4 个审计器全 exit 0。🐛 **bug 注入**：重新引入原缺陷 → **2 条测试失败**（检出为真）。📌 **请皇上决策**：① 合并 PR **#68**；② **#60→#61→#62→#63→#66→#67→#68** 自底向上 Merge；③ 确认 ADR-0018 Accepted；④（可选）打第一个 tag 验证发布链路——会触发**真实发布**，等合并后。run log: `strategy/runs/2026-11-06-2130.md` 🟢 |
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
| **v14 (Release Pipeline Audit)** | 🟢 **DoD #1–#7 全部交付 + 审计器自身已修 + 审计覆盖率已审计** — `scripts/release_audit.py`（自研 YAML 子集解析器，**不引入 PyYAML**）+ 6 项门禁 + `--strict` 严格超集 + `release.yml` **6 处缺陷全修** + **kind 分级** + **100 条 hermetic 测试** + **CI `release-audit` job 已入 `pr-coverage-gate.needs`** + **v134 新增 `scripts/audit_coverage_audit.py`（审计审计器）+ 32 条 hermetic 测试 + CI `audit-coverage-audit` job 已入 `pr-coverage-gate.needs`**|
| **审计覆盖率（元审计）** | ✅ **已闭合** — `audit_coverage_audit --strict` **exit 0**（3 个审计调用全部覆盖全部 2 个 workflow）；`ci.yml` 的 `release-audit` 已改为**默认 glob**（此前收窄到 `release.yml`）；**实测证明 v133 刚修的 `ci.yml` 权限缺陷此前删掉就绿**；重新收窄 → **exit 1** |
| **发布流水线状态** | ✅ **从「首次发布必然 exit 128」修到「经审计且逻辑正确」** — 正确解法是 `git tag --points-at HEAD` + `grep -v` **排除当前 tag**（单纯 `git describe --tags` 会解析出**正在发布的那个 tag**，把「崩溃」换成「changelog 永远为空」的**静默错误**）；真建 git repo 实测四种 tag 场景全对；第三方 action 已钉**真实上游 SHA** |
| **本轮 PR** | 🟢 **v14 审计覆盖率审计**：**待建**（`feat/v14-audit-coverage-audit` → `feat/v14-release-audit`）—— `audit_coverage_audit.py`（新，审计审计器）+ `test_audit_coverage_audit.py`（新，**32 条**）+ `ci.yml` 调用去收窄 + **新增 `audit-coverage-audit` CI job**；
| **上一轮 PR** | 🟢 **v14 Release Pipeline Audit**：**PR #68**（`feat/v14-release-audit` → `feat/v13-pr-coverage-audit`）—— `release_audit.py`（新）+ **kind 分级修复** + `test_release_audit.py`（新，**100 条**）+ `release.yml` 修复 + `ci.yml` **权限修复**；**待皇上 Merge** |
| **v13 stack** | ✅ 拓扑缺陷已修复 — PR #63/#66 的 `diverged-duplicate` 已消除；**`stack_topology_audit --strict` exit 0，5/5 links linear**；6 个 PR 现可自底向上无冲突合并 |
| **待合 PR #67/#66/#63/#62/#61/#60** | 🟢 全部 **OPEN + CLEAN + MERGEABLE + CI 全绿**；#67 head = `833bcf6`、#66 head = `e3d5626`（已 push + 远端回读校验）|
| **CI 触发覆盖 / PR 级 CI 覆盖** | ✅ 已闭合 — `ci_trigger_audit` / `pr_coverage_audit` 门禁 + 自举 CI job；**6/6 PR verified** |
| **门禁模式单调性 / CI 审计器环境无关性** | ✅ 已闭合 — 两模式共用唯一判定函数 `evaluate_gate()`，严格集合是默认集合**严格超集**；审计器已脱离 `GH_TOKEN` 隐式依赖 |
| **CI 安全审计** | ✅ **master 已脱险**：pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（63 CVE → 0）|


## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 所有会读到 CHANGELOG 的使用者 / 未来的每一个贡献者
- **v134 早场价值（本轮）**：
  1. **把一个无守卫的缺陷变成有守卫的** —— v133 刚修好的 `ci.yml` 权限缺陷，此前**删掉就绿**（实测）；现在删掉会红
  2. **闭合了一整个缺陷类，不只是一个实例** —— 任何未来的收窄（不只是这个调用点）都会被自动抓住
  3. **实证了「有 CI 证据 ≠ CI 证据有效」** —— 上一轮主题文档里的「exit 0」**恰好**绕开了唯一的 bug；本轮给出了对照实验（同文件直给审计器 → exit 1）
  4. **证明了「覆盖率是整体属性」** —— 与 v132 晚场「四个『对的』排除叠加」是同一形状的第二次出现；所以解法必须是**一个机器检查**，而不是逐个调用点自觉
  5. **32 条 hermetic 测试 + bug 注入检出为真** —— 重新收窄 → 新审计 exit 1
  6. **延续上轮的误报控制** —— `pr_coverage_audit.py` 被排除在受审名单外，**窄而准**（误报是有害的，会把真缺陷淹掉）
  7. **捕获了一个「静默降级」级 bug** —— `run: |` 块标量解析失败会让审计找到 **0 个**调用且**不报错**（本仓每个多行 CI step 都是 `run: |` 写的）

- **v134 早场价值边界（诚实降级，不夸大）**：
  - 本轮交付的是**「收窄不再能静默通过」**，**不是**「审计覆盖率已达最优」
  - 本审计只覆盖**已知受审脚本**的显式 `--workflow` 收窄；**不**检测其他收窄方式（环境变量、软链、限定 glob 模式）
  - `ci.yml` 的权限修复与新 job **尚未经 CI 实跑验证**（需 PR 的 CI 跑完）
  - **合并权归皇上**（`spec/CHARTER.md` 第 7 步），本轮只交付不合并
  - **端到端发布仍未验证** —— 需要真实 tag，属需皇上决策的动作

- **更早轮次（v133 晚场及之前）的价值确认**：已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`。