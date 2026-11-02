# NEXT_ROUND_THEME.md — ml-decision-boundary v127 晚场（v13 DoD #16 CI 门禁强度单调性完成）

**更新时间：** 2026-11-02 21:38 CST / 2026-11-02 13:38 UTC
**版本：** v127 晚场
**维护人：** 太子

---

## 🟢 v127 晚场 状态：**v13 DoD #16（CI 门禁强度单调性）完成，P0/P1/P1'/P1'' 全绿**

### 本轮交付：v13 DoD #16 — 门禁模式必须单调

| 交付物 | 内容 |
|--------|------|
| `scripts/pr_coverage_audit.py` | **改**：`evaluate_gate()` 单一判定点 + `DEFAULT_REQUIREMENTS` / `REQUIRE_CHECKS_REQUIREMENTS`（严格超集）+ `_requirement_failed()` + `_count_completed_checks()` + `completed_checks` 字段 + `has_completed_checks` + `--json` 输出 `gate` 字段 + `main()` 两模式统一走 `evaluate_gate()` |
| `tests/test_pr_coverage_audit.py` | **改**：22 → **42** 测试；同义反复的 `TestRequireChecks` 整类删除 → `TestGateModel` / `TestCheckCounting` / `TestCliUsesTheSharedGate` |
| `.github/workflows/ci.yml` | **改**：新增 `pr-coverage-gate` job（`needs:` 全部 8 job + `pull_request` 事件守卫）|
| `docs/REPRODUCE.md` | **改**：P1'' 节新增「两种门禁模式：严格模式永远不比默认模式宽松」小节 |
| `docs/adr/ADR-0018-v13-dod.md` | **改**：新增 DoD #16（门禁模式单调性）+ 设计约束 |
| `spec/phases.md` | **改**：新增对应 checklist 项 |
| `strategy/runs/2026-11-02-2138.md` | **新** 本轮 run log |

### 问题：一个号称「更严格」的门禁，实际比默认模式更宽松

上一轮（v127 早场）加的 `--require-checks` 是这样判的：

```python
missing = [c.number for c in coverages if c.observed_checks == 0]
```

而默认模式判 `summary["ok"]`，即所有 `c.is_verified` 为真 —— 后者要求**四件事同时成立**：

| # | 条件 |
|---|------|
| 1 | head 分支 workflow 订阅了 `pull_request`（`workflow_subscribes`）|
| 2 | 该 workflow 的过滤器覆盖**这个 PR 自己的** base 分支（`base_covered`）|
| 3 | GitHub 实际报告了 checks（`observed_checks > 0`）|
| 4 | 审计得出了结论（无 `problems`）|

**严格模式对第 1、2 条完全不看。** 于是：

```
PR 状态                observed_checks   默认模式   --require-checks
not-subscribed              7              FAIL          PASS    ← 错了
base-not-covered            7              FAIL          PASS    ← 错了
```

一个 **CI 从来不会为它触发**的 PR，只要身上还挂着**上一次运行留下的陈旧 checks**，
就能从号称「更严格」的门禁里溜过去 —— **比默认模式更宽松的门禁，
看上去像安全网，实际是个筛子**。

### 顺带挖出的元缺陷：上一轮的测试是同义反复

v127 早场遗留的 `TestRequireChecks` 把判定逻辑**在测试里重新实现了一遍**：

```python
# Simulate the CLI's --require-checks decision logic
def require_checks_gate(coverages):
    missing = [c.number for c in coverages if c.observed_checks == 0]
    return 1 if missing else 0
```

**测的是测试自己** —— 把 CLI 的 flag 整个删掉照样全绿。它甚至把要修的 bug
原样抄进了断言里，于是**测试在保护 bug**：任何修复都会让它变红。

### 解法

**1. 把「这个门禁过不过」收敛到唯一一个函数 `evaluate_gate()`**

```python
DEFAULT_REQUIREMENTS = ("subscribes", "base_covered", "checks", "auditable")
REQUIRE_CHECKS_REQUIREMENTS = DEFAULT_REQUIREMENTS + ("checks_completed",)
```

两种模式只做一件事：**传入不同的要求集合**。因为严格集合是默认集合的
**严格超集**，单调性由**构造**保证 —— 不再依赖两段代码「碰巧」写对。

**2. 新增第五个要求 `checks_completed`**

GitHub 在 workflow **开始**时就创建 check run → `observed_checks` 把还在排队的也算进去。
**「有 check」和「check 跑完了」是两件事。** 新增 `_count_completed_checks()`，
`PrCoverage` 加 `completed_checks` 字段，报告行改为 `checks seen : 6 (6 finished)`。

> 实测出来的边界情况：GitHub 会返回 `status=COMPLETED` + `conclusion=null`
> 的 check run（跑完了但无结论）。第一版只认结论词汇 → 严格门禁对这种 PR
> **永远不可能满足**。修正为「结论是终态 **或** 状态是 `COMPLETED`」。

**3. 测试全部重写为调用真实代码路径**，并加 bug 注入验证：

```
FAILED TestGateModel::test_strict_requirements_are_a_strict_superset
FAILED TestGateModel::test_strict_mode_is_never_laxer_than_default
FAILED TestGateModel::test_the_original_bug_is_fixed
FAILED TestGateModel::test_queued_checks_fail_the_strict_gate_only
4 failed, 35 passed        ← 重新注入原 bug，必须有测试失败
```

**4. CI 接线：独立 job，不是并行 job 里的一个 step**

严格门禁要问「checks 跑完了吗」，这问题**只有在兄弟 job 跑完之后**才答得上来。
实测 run `41314763785`：`pr-coverage-audit` 完成于 14:09:38，
`hyperparam-sweep` 完成于 14:11:11 —— **晚了 93 秒**。8 个 job 是**并行**的。

→ 做成独立 job `pr-coverage-gate`，用 `needs:` 显式声明顺序。
→ 另：CI 也在 `push` 上触发，`github.event.pull_request.number` 为空 →
`argparse` 报 `invalid int value: ''` → 门禁无故把构建弄红。
→ 故加 `if: github.event_name == 'pull_request'` 守卫 + 非 PR 事件显式 `exit 0`。

> 教训：**门禁自身不能成为 flaky 源**。一个「要求所有 checks 都跑完」的门禁，
> 如果和被它检查的 checks 并行运行，就等于自己给自己设了一颗定时炸弹。

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-02 21:38** | 🟢 **v127 晚场 #1：v13 DoD #16「CI 门禁强度单调性」全部交付。** 🔍 **本轮开工实测发现一个号称「更严格」的门禁，实际比默认模式更宽松**：上一轮（v127 早场）加的 `--require-checks` 只检查 `observed_checks == 0`，而默认模式判 `summary["ok"]`（要求 `workflow_subscribes` + `base_covered` + `observed_checks > 0` + 无 problems **四者同时成立**）。**严格模式对前两条完全不看** → 一个 **CI 从来不会为它触发**的 PR（`not-subscribed` / `base-not-covered`），只要身上还挂着**上一次运行留下的陈旧 checks**，就能从「严格」门禁里溜过去。**一个比默认模式更宽松的门禁，看上去像安全网，实际是个筛子** —— 而且是那种「今天跑绿、明天出事」的筛子：只有当某个 PR 真的处于 unverified 状态时才会漏，而这恰恰是最需要门禁生效的时刻。🆕 **解法**：① 判定收敛到**唯一**函数 `evaluate_gate()`，两种模式只传不同的**要求集合**（`DEFAULT_REQUIREMENTS` / `REQUIRE_CHECKS_REQUIREMENTS`），严格集合是默认集合的**严格超集** → 单调性由**构造**保证，不再依赖两段代码「碰巧」写对 ② 新增第五个要求 `checks_completed` —— GitHub 在 workflow **开始**时就创建 check run，「有 check」和「check 跑完了」是两件事；新增 `_count_completed_checks()` + `completed_checks` 字段 + 报告行 `checks seen : 6 (6 finished)`；**实测边界情况**：GitHub 会返回 `status=COMPLETED` + `conclusion=null`，第一版只认结论词汇 → 严格门禁对这种 PR 永远不可能满足，已修正 ③ **顺带挖出上一轮的元缺陷**：`TestRequireChecks` 把判定逻辑**在测试里重新实现了一遍**（同义反复），把 CLI 的 flag 整个删掉照样全绿，**测试在保护 bug**；已整类删除并重写为调用真实 `evaluate_gate()`，并加 **bug 注入验证**（重新注入原 bug → 4 个测试失败）④ **CI 接线用独立 job**：实测 run `41314763785` 中 `pr-coverage-audit` 完成于 14:09:38 而 `hyperparam-sweep` 完成于 14:11:11（**晚 93 秒**），8 job 并行 → 把 `--require-checks` 放进同一 job 会**因为错误的原因失败**；故做成 `pr-coverage-gate` 独立 job + `needs:` 显式排序；另加 `if: github.event_name == 'pull_request'` 守卫（CI 也在 `push` 上触发，`pull_request.number` 为空会让 argparse 报错并无故弄红构建）。✅ P0 ✅ + P1 ✅（**671 passed / 5 skipped / 2 pre-existing timeout FAILED**，`test_benchmarks_full_suite_runs` + `test_cli_health_runs` 在 base commit `5035430` 上同样失败，与本轮无关）+ P1' ✅（exit 0，6 个 base 分支全覆盖）+ P1'' ✅（**6/6 PR verified**）+ **P1'' strict ✅**（**6/6**，全部 `6 finished`）+ **bug 注入 ✅**（**4 个测试失败** —— 新测试确实咬得住）+ **YAML ✅**（`ci.yml` 解析通过，9 job，`needs` 正确）+ **CI 专项 ✅**（68 passed）。💡 **本轮最重要的产出不是「加了 20 个测试」**：是 **一个号称更严格的门禁，实际比默认模式更宽松**，这个缺陷被修掉了；而且**顺带挖出上一轮的测试在保护 bug**（同义反复，把待修逻辑在测试里抄了一遍）。一个门禁如果比它要替代的模式更宽松，它就不是门禁，是**伪装成安全网的筛子**；一个测试如果测的是自己，它就不是测试，是**给 bug 盖的图章**。📌 **请皇上决策**：① **Merge PR #67**（v13 DoD #8 + #14 + **#16**，待 Merge）② Merge PR #66（v13 DoD #7）③ Merge PR #63（v13 DoD #4 + #6）④ Merge PR #62 ⑤ Merge PR #61 ⑥ Merge PR #60 ⑦ 接受 ADR-0018。run log: `strategy/runs/2026-11-02-2138.md` 🟢 |
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
| **本轮 PR** | 🟢 **PR #67 已更新**（v127 晚场交付 `feat/v13-pr-coverage-audit`，DoD #8 + #14 + **#16**）|
| **CI 触发覆盖** | ✅ **已闭合** — `pull_request` 无 `branches:` 过滤器；`scripts/ci_trigger_audit.py` 门禁（exit 0/1）+ CI `ci-trigger-audit` 自举 job |
| **PR 级 CI 覆盖** | ✅ **已闭合** — `scripts/pr_coverage_audit.py` 门禁（exit 0/1）+ CI `pr-coverage-audit` 自举 job；**6/6 PR verified** |
| **门禁模式单调性** | ✅ **已闭合** — 两种模式共用唯一判定函数 `evaluate_gate()`；`--require-checks` 要求集合是默认的**严格超集**（+`checks_completed`）；新增独立 CI job `pr-coverage-gate`（`needs:` 全部 8 job + `pull_request` 事件守卫）|
| **CI 审计器环境无关性** | ✅ **已闭合** — head 分支 workflow 改为从 **GitHub Contents API** 读取（本地 git 降级为 fallback）；hermetic 测试；CI runner 上 `pr-coverage-audit` job **SUCCESS** |
| **待合 PR #67** | 🟢 **PR #67 OPEN + CLEAN + MERGEABLE**（v13 DoD #8 + #14 + **#16**，待皇上 Merge）|
| **待合 PR #66** | 🟢 **PR #66 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #7，待皇上 Merge）|
| **待合 PR #63** | 🟢 **PR #63 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #4 + #6，待皇上 Merge）✅ **已通过回移修复获得首次 CI 验证**|
| **待合 PR #62** | 🟢 **PR #62 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #2-#4，待皇上 Merge）|
| **待合 PR #61** | 🟢 **PR #61 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #1 provenance capture，待皇上 Merge）|
| **待合 PR #60** | 🟢 **PR #60 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v12 三 DoD，待皇上 Merge）|
| **本轮分支** | `feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）|
| **v13 DoD #7** | ✅ **CI 触发覆盖闭合完成** — 修复 `pull_request: branches: [master]` 过滤器 + `scripts/ci_trigger_audit.py` 可执行门禁 + CI 自举 job + 19 测试 |
| **v13 DoD #8** | ✅ **PR 级 CI 覆盖验证完成** — `scripts/pr_coverage_audit.py` 可执行门禁 + CI 自举 job + 回移修复使 PR #63 首次获得 CI |
| **v13 DoD #14** | ✅ **CI 审计器环境无关性完成** — head 分支 workflow 改为从 GitHub Contents API 读取 + `resolve_workflow_at()` + `workflow_source` 字段 + hermetic 测试 + CI job 增加全量分支 fetch |
| **v13 DoD #16** | ✅ **门禁模式单调性完成** — `evaluate_gate()` 单一判定点 + 严格超集要求集合 + `completed_checks` / `checks_completed` 要求 + 测试 22→**42** + bug 注入验证（4 failed）+ CI 独立 `pr-coverage-gate` job |
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
- **验证**：
  - 本地 P0 ✅ compileall 0 + import smoke OK
  - 本地 P1 ✅ **671 passed / 5 skipped / 2 pre-existing timeout**（`test_benchmarks_full_suite_runs` + `test_cli_health_runs` 在 base commit `5035430` 上同样失败，非本轮引入）
  - 本地 P1' ✅ `ci_trigger_audit.py` exit 0（6 个 base 分支全覆盖）
  - 本地 P1'' ✅ `pr_coverage_audit.py` exit 0（**6/6 PR verified**）
  - 本地 P1'' strict ✅ `--require-checks` exit 0（**6/6**，全部 `6 finished`）
  - **bug 注入 ✅** 重新注入原 bug → **4 个测试失败**（新测试确实咬得住）
  - **YAML ✅** `ci.yml` 解析通过，9 个 job，`pr-coverage-gate.needs` 正确
  - **CI 专项 ✅** 68 passed（trigger / workflow / ci 相关）
- **当前状态**：🟢 **无外部阻塞** — v13 DoD #1-#8 + #12-#16 全部交付且本地 P0–P1'' 全绿；待皇上 Merge PR #60 / #61 / #62 / #63 / #66 / #67 + 接受 ADR-0018
- **最近一次验证**：2026-11-02 21:38 CST（v127 晚场 #1）
- **master HEAD**：`4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**：`feat/v13-pr-coverage-audit`（base `feat/v13-ci-trigger-coverage`）
- **阻塞**：无（PR #60 / #61 / #62 / #63 / #66 / #67 待 Merge，不阻塞下一轮开发）
- **⚠️ 价值已完全实现**：**一个号称更严格的门禁比默认模式更宽松** —— 这个缺陷被修掉了，并且**用 bug 注入证明新测试确实咬得住**。门禁的强度现在由**构造**保证（严格集合是默认集合的超集），而不是由两段代码「碰巧」一致保证。
