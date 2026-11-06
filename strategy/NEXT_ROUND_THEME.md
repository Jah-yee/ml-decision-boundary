# NEXT_ROUND_THEME.md — ml-decision-boundary v133 晚场（v14 审计器修 bug + kind 分级 + ci.yml 权限缺陷修复）

**更新时间：** 2026-11-06 21:30 CST / 2026-11-06 13:30 UTC
**版本：** v133 晚场
**维护人：** 太子
**本轮 run log：** `strategy/runs/2026-11-06-2130.md`

---

## 🟢 v133 晚场 状态：**v14 审计器自身修 bug —— 「默认路径」从 exit 1 修到 exit 0；并因此暴露并修复了 `ci.yml` 缺 `permissions:` 的真实缺陷**

### 本轮交付：修审计器 + 修它抓出来的真缺陷

| 交付物 | 内容 |
|--------|------|
| **选题依据** | 上一轮 theme 白纸黑字写「`release_audit --strict` **exit 0（6/6）**」——**实测 exit 1**。上一轮大概率跑的是 `--workflow release.yml`（**单文件**，绕过了 bug），而**默认 glob**（带上 `ci.yml`）是坏的。**验收命令的写法，决定了验收是否有效。** |
| **`scripts/release_audit.py`** | **修**：`classify_workflow()`（按语义分 `release`/`ci`）+ `requirements_for(kind, strict)` + 要求集按 kind 分组 + `evaluate_gate()` 改 kind 感知 + `trigger_safe` **语义按 kind 反转** + 报告/JSON 带 kind |
| **`.github/workflows/ci.yml`** | **修**：补最小权限 `contents: read` / `pull-requests: read` —— 此前**完全没有 `permissions:` 块**，CI 的 `GITHUB_TOKEN` 继承仓库默认权限（多为 read-write），而**没有 job 需要写** |
| **`tests/test_release_audit.py`** | **68 → 100 条**（新增 6 类：分类 / kind 作用域要求集 + 跨 kind 单调性 / trigger 语义反转 / **默认 glob 路径** / 真实仓库 kind 划分 / bug 注入） |
| **run log** | `strategy/runs/2026-11-06-2130.md`（新，含全部推导与证据） |
| **PR** | **#68** → base `feat/v13-pr-coverage-audit`，待 Merge |

### 核心修复：把「发布专用门禁」与「CI 门禁」分开

- **release**：必须由 `push` + `tags:` 触发；查 tag 发现 / changelog 完整性 / concurrency
- **ci**：**不得**只由 tag 触发，且**必须**有 `push` 或 `pull_request`；不查 tag 发现 / changelog / concurrency
- **单调性**：对**每一种** kind，strict 要求集是 default 要求集的**严格超集**（由构造保证）
- **原 bug**：`--strict`（默认 glob）把发布专用门禁施加到 `ci.yml` → **6 项全挂、exit 1**

### 元观察（本轮最值钱的一条）

**误报不只是噪音——误报是有害的。**
上一轮把 `ci.yml` 判成 6 项全挂（其中 4 项是误报），**没人会去分辨哪几颗是真的**。
于是 `ci.yml` 真正缺 `permissions:` 块这个**真实缺陷**，被淹没在 4 颗假警报里，**没人看见**。
修好分类后，`ci.yml` 只剩 **1 项红——而那一项是真的**。

**一个把对的东西判成错的审计，会让真缺陷变得看不见。**

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
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
| **v14 (Release Pipeline Audit)** | 🟢 **DoD #1–#7 全部交付 + 审计器自身已修** — `scripts/release_audit.py`（自研 YAML 子集解析器，**不引入 PyYAML**）+ 6 项门禁 + `--strict` 严格超集 + `release.yml` **6 处缺陷全修** + **kind 分级**（`release`/`ci` 要求集分开，`trigger_safe` 语义反转）+ **100 条 hermetic 测试**（19 类，含 6 条新增 bug 注入）+ **CI `release-audit` job 已入 `pr-coverage-gate.needs`** + `job_graph_audit --strict` exit 0（11 jobs）|
| **审计器默认路径** | ✅ **已闭合** — `--strict` **默认 glob**（`.github/workflows/*.yml`，2 workflows）**exit 0**；上一轮的自述「exit 0」**不成立**（实测 exit 1，因走的是单文件路径绕过了 bug）；**修好后暴露并修复了 `ci.yml` 缺 `permissions:` 的真实缺陷** |
| **发布流水线状态** | ✅ **从「首次发布必然 exit 128」修到「经审计且逻辑正确」** — 正确解法是 `git tag --points-at HEAD` + `grep -v` **排除当前 tag**（单纯 `git describe --tags` 会解析出**正在发布的那个 tag**，把「崩溃」换成「changelog 永远为空」的**静默错误**）；真建 git repo 实测四种 tag 场景全对；第三方 action 已钉**真实上游 SHA** |
| **本轮 PR** | 🟢 **v14 Release Pipeline Audit**：**PR #68**（`feat/v14-release-audit` → `feat/v13-pr-coverage-audit`）—— `release_audit.py`（新）+ **kind 分级修复** + `test_release_audit.py`（新，**100 条**）+ `release.yml` 修复 + `ci.yml` **权限修复**；**待皇上 Merge** |
| **v13 stack** | ✅ 拓扑缺陷已修复 — PR #63/#66 的 `diverged-duplicate` 已消除；**`stack_topology_audit --strict` exit 0，5/5 links linear**；6 个 PR 现可自底向上无冲突合并 |
| **待合 PR #67/#66/#63/#62/#61/#60** | 🟢 全部 **OPEN + CLEAN + MERGEABLE + CI 全绿**；#67 head = `833bcf6`、#66 head = `e3d5626`（已 push + 远端回读校验）|
| **CI 触发覆盖 / PR 级 CI 覆盖** | ✅ 已闭合 — `ci_trigger_audit` / `pr_coverage_audit` 门禁 + 自举 CI job；**6/6 PR verified** |
| **门禁模式单调性 / CI 审计器环境无关性** | ✅ 已闭合 — 两模式共用唯一判定函数 `evaluate_gate()`，严格集合是默认集合**严格超集**；审计器已脱离 `GH_TOKEN` 隐式依赖 |
| **CI 安全审计** | ✅ **master 已脱险**：pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（63 CVE → 0）|


## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 所有会读到 CHANGELOG 的使用者 / 未来的每一个贡献者
- **v133 晚场价值（本轮）**：
  1. **修好了审计器自身的 bug** —— 默认路径 `--strict` 从 **exit 1 → exit 0**；上一轮的自述「exit 0（6/6）」**不成立**，本轮把它**真的做成了**
  2. **揭示并修复了一个此前从未被发现的真实安全缺陷** —— `ci.yml` **完全没有 `permissions:` 块**，CI 的 `GITHUB_TOKEN` 继承仓库默认权限（**多为 read-write**），而**没有任何 CI job 需要写**；已补最小权限
  3. **证明了「误报是有害的」** —— 上一轮把 `ci.yml` 判成 6 项全挂（4 项误报），真缺陷被淹没；修好分类后只剩 1 项红，**而那一项是真的**。**信噪比是发现真缺陷的唯一预算**
  4. **证明了「CI 绿 ≠ 工具对」** —— CI job 恰好显式传了单文件，**恰好**绕开了唯一的 bug，所以上一轮**有** CI 证据而那个证据**无效**。CI 是**执行者**的证据，不是**设计者**的证据
  5. **证明了「验收命令的写法，决定了验收是否有效」** —— 只验「我指定的那条路径」的验收，和**没验**信息量上几乎没有区别；本轮补上了**默认 glob 路径**的测试
  6. **测试 68 → 100，且 bug 注入检出为真** —— 重新引入原缺陷 → **2 条测试失败**
  7. **跨 kind 单调性由构造保证** —— 对**每一种** kind，strict 要求集都是 default 的**严格超集**；且用测试把「按 kind 豁免」这条**后门焊死**（曾经是 release、后来丢了 `tags:` 过滤的 workflow **仍按 release 判定**且**仍被抓住**）

- **v133 晚场价值边界（诚实降级，不夸大）**：
  - 本轮交付的是**「审计器从「默认路径报错」修到「默认路径正确」」**，**不是**「发布已经成功」
  - **端到端发布仍未验证** —— 需要一个真实 tag 才能验证，而打 tag 触发真实发布**属于需皇上决策的动作**，本代理不擅自执行
  - **合并权归皇上**（`spec/CHARTER.md` 第 7 步），本轮只交付不合并
  - `ci.yml` 的权限修复**尚未经 CI 实跑验证**（需 PR #68 的 CI 跑完）
- **更早轮次（v131 晚场及之前）的价值确认**：已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`。