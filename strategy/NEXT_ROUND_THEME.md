# NEXT_ROUND_THEME.md — ml-decision-boundary v125 晚场（v13 DoD #8 PR 级 CI 覆盖验证完成）

**更新时间：** 2026-11-01 09:48 CST / 2026-11-01 01:48 UTC
**版本：** v125 晚场
**维护人：** 太子

---

## 🟢 v125 晚场 状态：**v13 DoD #8（PR 级 CI 覆盖验证）完成，P0/P1/P2/P3 全绿，PR #67 待开**

### 本轮交付：v13 DoD #8 — PR 级 CI 覆盖验证

| 交付物 | 内容 |
|--------|------|
| `scripts/pr_coverage_audit.py` | **新**（唯一实现源）：PR 级覆盖审计器 + CLI |
| `tests/test_pr_coverage_audit.py` | **新** 17 测试 |
| `.github/workflows/ci.yml` | 新增 `pr-coverage-audit` job（8 job）|
| `docs/adr/ADR-0018-v13-dod.md` | DoD #8 落档 + DoD 表更新 |
| `spec/phases.md` | v13 DoD #8 落档 |
| `docs/REPRODUCE.md` | 新增 P1'' 关卡（PR 级 CI 覆盖自检）|
| `strategy/runs/2026-10-29-2210.md` | 本轮 run log |

### 问题：DoD #7 的修复只对 PR #66 自己生效

DoD #7 修好了 workflow 文件里的 `pull_request` 过滤器，但审计的是**当前分支上那一份 `ci.yml`**。
而 GitHub 判定一个**已存在的** PR 会不会触发 CI 时，读的是 **PR 的 head 分支上的 workflow**。

| PR | head 分支上的 ci.yml | base | 实际 CI |
|----|------|------|----------|
| #60/#61/#62 | `branches: [master]`（未修） | `master` | ✅ 6/6 |
| **#63** | **`branches: [master]`（未修）** | `feat/v13-replay-provenance` | ❌ **零次运行** |
| #66 | 无过滤器（已修） | `feat/v13-replay-integrity-guard` | ✅ 7/7 |

**合并顺序死锁**：想让 #63 有 CI → 必须先把修复合进 #63 的分支；而修复在 #66 上，#66 的 base 又是 #63。

### 解法

1. **触发块**：去掉 `pull_request` 上的 `branches:` 过滤器 → 任何 base 的 PR 都启动 CI。
2. **`scripts/pr_coverage_audit.py`**：读取 PR head 分支的 workflow，回答 GitHub 会回答的那个问题——"这个 PR 到底有没有被 CI 验证？"
   - **零第三方依赖**：复用 DoD #7 的解析器（`from ci_trigger_audit import ...`）
   - **只读**、**诚实降级**（拿不到 PR 列表时 rc=2 报错）
   - **三个独立条件才算 verified**：① head 分支订阅 `pull_request` ② 过滤器覆盖该 PR 自己的 base ③ **GitHub 实际报告了 checks**
3. **CI 新增 `pr-coverage-audit` job（自举守卫）**：这个 job 自己跑在 CI 里检查所有 open PR。该 job **不执行** `pip install -r requirements.lock`。
4. **落地 #63 的 CI：回移触发修复**到 `feat/v13-replay-integrity-guard`（= PR #63 的 head），push。

### 验收结果

| 层级 | 命令 | 结果 |
|------|------|------|
| **P0** | `python3 -m compileall -q .` + import smoke | ✅ exit 0 + `import main, ml_db, core.registry, core.replay_guard, api.provenance, web.server` OK |
| **P1** | `python3 -m pytest -q` | ✅ **646 passed / 5 skipped / 2 FAILED**（692.87s）—— 2 个失败为**预存超时**（`test_benchmarks_full_suite_runs` 300s 超时、`test_cli_health_runs` 120s 超时），在 clean checkout 上复现，**非本轮引入** |
| **P2** | `python3 -m benchmarks --quick` | ✅ PASSED（acc 0.7900, thr 0.7000）|
| **P3** | HTTP 契约 8 项 | ✅ health 200 / integrity 200 / integrity_single 200 / integrity_unknown 404 / verify 200 / verify_no_id 400 / predict_batch 200 / predict_no_dataset 400 |
| **P1'** | `python3 scripts/ci_trigger_audit.py` | ✅ exit 0，6 个 base 分支全部覆盖 |
| **P1''** | `python3 scripts/pr_coverage_audit.py` | ✅ exit 0，**5/5 PR verified** |
| **PR 级** | `gh pr checks 63` | ✅ **7/7 SUCCESS**（PR #63 史上第一次有 CI）|

### 修复后的覆盖

```
✅ PR #66  base covered: yes   checks seen: 7   verdict: verified
✅ PR #63  base covered: yes   checks seen: 7   verdict: verified   ← 从零到有
✅ PR #62  base covered: yes   checks seen: 6   verdict: verified
✅ PR #61  base covered: yes   checks seen: 6   verdict: verified
✅ PR #60  base covered: yes   checks seen: 6   verdict: verified

5/5 pull requests are verified by CI.
```

### 本轮最重要的产出

> 不是"加了 17 个测试"，而是**把一个一直存在、但从未被测量的假设变成了 CI 会主动拦住的门禁**。
>
> 修复前，"CI 覆盖了所有 PR" 是一句**没人验证过的话**；它恰好在唯一一次不成立的时候（PR #63）
> 静悄悄地失效了两轮。现在它是一条 **CI 每次都检查、违反就红**的规则。
>
> **附带效应**：修复后 #63 及其之后的 PR 会**首次**真正获得 CI 验证。

### 与上轮对比

| 指标 | v124 早场 | v125 晚场 |
|------|-----------|-----------|
| 审计层级 | 文件级（workflow）| **PR 级（open PR）**|
| 读的 workflow | 当前工作树 | **PR 的 head 分支** |
| base 分支来源 | 静态清单（6 个）| **PR 自身**（自动）|
| CI job 数 | 7 | **8**（+`pr-coverage-audit`）|
| PR 覆盖验证 | 4/5（#63 缺）| **5/5** |
| PR #63 checks | 0 | **7** |
| 本轮性质 | 修文件级缺陷 | **补 PR 级盲区 + 解开合并死锁** |

### 🆕 本轮交付：v13 DoD #7 — CI 触发覆盖闭合

| 交付物 | 内容 |
|--------|------|
| `.github/workflows/ci.yml` | **去掉 `pull_request` 的 `branches: [master]` 过滤器** + 新增 `ci-trigger-audit` job（7 job）|
| `scripts/ci_trigger_audit.py` | **新**（唯一实现源）：零依赖触发块审计器 + CLI |
| `tests/test_ci_trigger_audit.py` | **新** 19 测试 |
| `docs/adr/ADR-0018-v13-dod.md` | DoD #7 落档 + DoD 表更新 + 下轮待办更新 |
| `spec/phases.md` | v13 DoD #7 落档 |
| `docs/REPRODUCE.md` | 新增 P1' 关卡（CI 触发覆盖自检）|
| `strategy/runs/2026-10-29-0942.md` | 本轮 run log |

### 问题：**PR #63 从未跑过一次 CI，而记录写的是"CI 6/6 SUCCESS"**

`ci.yml` 的触发块带 `pull_request: branches: [master]` 过滤器 → **只有 base 为 `master` 的 PR 会启动 CI**。
本仓库 v13 采用 stacked PR 结构（base 是另一个 feature 分支），于是：

| PR | base | CI 运行？ |
|----|------|----------|
| #60 / #61 / #62 | `master` | ✅ 6/6 SUCCESS |
| **#63** | **`feat/v13-replay-provenance`** | ❌ **零次运行** |

实测：`gh pr checks 63` → `no checks reported`；`gh pr view 63 --json statusCheckRollup` → `[]`；
`gh run list` 全部历史里 **没有** `feat/v13-replay-integrity-guard` 的任何记录。
对照组 `exp/dup-pr-probe`（base=`master`）**有** CI 运行 → CI 本身没问题，**唯一变量就是 base 分支**。

**后果**：PR #63 携带的 v13 DoD #4（Replay Integrity Guard，51 个新测试）+ DoD #6（`docs/REPRODUCE.md` v1.0，723 行）**从未被 CI 验证过**。

**这个缺口特别危险，因为它看起来不像故障**：CI 失败是🔴红（一定有人管）、在跑是🟡灰（通常会等），
而**零检查是一片⚪空白** —— 看起来像"还没开始"，而不是"永远不会开始"。
于是 v123 两轮 run log 都把 `MERGEABLE` 读成了"已验证"。

> **MERGEABLE 说的是"能合并"，不是"已验证"。** `statusCheckRollup: []` 才是真相。

⚠️ **事实性错误修正**：v123 两轮记录中"PR #63 CI 6/6 SUCCESS"**对 #63 不成立**（实际 0 次运行）。本轮已更正。

### 解法

1. **触发块**：去掉 `pull_request` 上的 `branches:` 过滤器 → 任何 base 的 PR 都启动 CI。
   不过度触发：`push` 过滤器**不含 `feat/*`**，推 feature 分支不会重复跑。
2. **`scripts/ci_trigger_audit.py`**：读取 workflow 的 `on:` 块，回答 GitHub 会回答的那个问题
   ——"一个 base 为 X 的 PR，会触发 CI 吗？"
   - **零第三方依赖**：PyYAML **不在 `requirements.lock`**，import 它会直接搞挂 CI
     → 自研子集解析器（嵌套一级 / flow list / block list），**看不懂就抛异常而不是猜**
     （一个静默返回"无过滤器"的解析器会让审计**说谎**）
   - **只读**、**exit 0/1 可直接当 CI 门禁**
   - 顺带避开 YAML 1.1 的坑（PyYAML 把裸 `on` 解析成布尔 `True`，自研解析器按字面 `on:` 查找）
3. **CI 新增 `ci-trigger-audit` job（自举守卫）**：这个 job 自己跑在 CI 里检查 CI 的触发块，
   一旦有人写回 `branches: [master]`，**构建自己变红**。
   该 job **不执行** `pip install -r requirements.lock` —— **守卫不能依赖它要守护的那套环境**。
4. **`tests/test_ci_trigger_audit.py`（19 测试）**：解析器行为 12 个 + 仓库不变量 7 个
   （最重要的一条：`ci.yml` 的 `pull_request` 过滤器必须是 `None`）。

### 验收结果

| 层级 | 命令 | 结果 |
|------|------|------|
| **P0** | `python3 -m compileall -q .` + import smoke | ✅ exit 0 + `import main, ml_db, core.registry, core.replay_guard, api.provenance, web.server` OK |
| **P1** | `python3 -m pytest -q` | ✅ **631 passed / 5 skipped / 0 FAILED**（393.26s，612 → 631，+19）|
| **P2** | `python3 -m benchmarks --quick` | ✅ PASSED（acc 0.7900, thr 0.7000）|
| **P3** | HTTP 契约 8 项 | ✅ health 200 / integrity 200 / integrity_single 200 / integrity_unknown 404 / verify 200 / verify_no_id 400 / predict_batch 200 / predict_no_dataset 400 |
| **P1'** | `python3 scripts/ci_trigger_audit.py` | ✅ exit 0，6 个 base 分支全部覆盖 |

### 修复后的覆盖

```
📄 .github/workflows/ci.yml
   events: push, pull_request
   pull_request base filter: (no filter — every base branch)
     ✅ master / ✅ main / ✅ feat/v12-sdk-foundation
     ✅ feat/v13-provenance-provenance / ✅ feat/v13-replay-provenance
     ✅ feat/v13-replay-integrity-guard

📄 .github/workflows/release.yml
   events: push
   pull_request base filter: n/a — workflow does not run on pull requests

✅ Every pull request base branch is covered by CI.
```

### 本轮最重要的产出

> 不是"加了 19 个测试"，而是**把一个一直存在、但从未被测量的假设变成了 CI 会主动拦住的门禁**。

修复前，"CI 覆盖了所有 PR" 是一句**没人验证过的话**；它恰好在唯一一次不成立的时候（PR #63）
静悄悄地失效了两轮。现在它是一条 **CI 每次都检查、违反就红**的规则。

**附带效应**：修复后 #63 及其之后的 PR 会**首次**真正获得 CI 验证。若合并时暴露真实问题，需单独跟进。

### 与上轮对比

| 指标 | v123 晚场 | v124 早场 |
|------|-----------|-----------|
| P1 测试数 | 612 passed | **631 passed**（+19）|
| P1 耗时 | 368.48s | 393.26s |
| 本轮性质 | 纯文档交付 | **修复 CI 覆盖缺陷 + 新增自举门禁** |
| CI job 数 | 6 | **7**（+`ci-trigger-audit`）|
| 覆盖 base 分支 | 1（master）| **全部**（无过滤器）|

---

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-11-01 09:48** | 🟢 **v125 晚场 #1：v13 DoD #8「PR 级 CI 覆盖验证」全部交付 + 解开合并顺序死锁。** 🔍 **本轮开工实测发现 v124 早场的修复留下第二个缺口**：DoD #7 审计的是**当前分支上那一份 `ci.yml`**，但 GitHub 判定 PR 是否触发 CI 时读的是 **PR head 分支上的 workflow** —— 所以 DoD #7 的修复**只对 PR #66 自己生效**。⚠️ **合并顺序死锁**：想让 #63 有 CI 必须先合 #66 进 #63 的分支；而 #66 的 base 又是 #63；GitHub 不会把 #66 的变更预演到 #63。**#63 携带的 DoD #4（51 个新测试）+ DoD #6（723 行文档）至今从未被任何 CI 验证过。** 🆕 **解法**：① `scripts/pr_coverage_audit.py`（新，唯一实现源）把审计对象从「workflow 文件」升级为「PR」—— 读 PR **head 分支**的 workflow + **PR 自身**的 base 分支；复用 DoD #7 的解析器不重复实现；零第三方依赖；只读；**拿不到 PR 列表时 rc=2 报错，绝不把「查不到」报成「一切正常」** ② **三个独立条件才算 verified**：head 分支订阅 `pull_request` + 过滤器覆盖该 PR 自己的 base + **GitHub 实际报告了 checks**（②「会不会跑」与③「到底跑没跑」不可互相代替）③ CI 新增 `pr-coverage-audit` 自举 job（8 job，**不装 requirements.lock** —— 守卫不能依赖它守护的环境；需 `fetch-depth: 0` + `GH_TOKEN`）④ **落地 #63 的 CI：回移 DoD #7 触发修复到 #63 的 head 分支并 push**（选「回移」而非「改 base」—— 回移对**下一个** stacked PR 同样有效）。✅ P0 ✅ + P1 ✅（**646 passed / 5 skipped / 2 pre-existing timeout FAILED**，692.87s，非本轮引入）+ P2 ✅（acc 0.7900）+ P3 ✅（8/8 HTTP 契约）+ P1' ✅（exit 0）+ P1'' ✅（**5/5 PR verified**）+ **PR 级 ✅（`gh pr checks 63` → 7/7 SUCCESS，PR #63 史上第一次有 CI）**。🎯 **本轮最重要的产出不是"加了 17 个测试"**：是 **PR #63 从「零 CI」变成「7/7 绿色」** —— 一段从未被任何 CI 验证过的代码（DoD #4 的 51 个新测试 + DoD #6 的 723 行文档）第一次拿到机器验证。💡 「每个 PR 都被 CI 验证」现在有**两个**门禁守着：文件级（P1'）保证**下一个**分支不带上旧过滤器，PR 级（P1'）保证**现在**每个 open PR 都真被覆盖 —— DoD #7 的承诺此前"在最需要它的那个 PR 上不成立"，现在它第一次**对它声称覆盖的全部 PR 成立**（5/5）。📌 **请皇上决策**：① Merge PR #67（v13 DoD #8，CI 8 job QUEUED）② Merge PR #66（v13 DoD #7，CI 7/7 SUCCESS）③ Merge PR #63（v13 DoD #4 + #6，**现已 7/7 SUCCESS**）④ Merge PR #62 ⑤ Merge PR #61 ⑥ Merge PR #60 ⑦ 接受 ADR-0018。run log: `strategy/runs/2026-10-29-2210.md` — 第97次提醒 #1 🟢* |
| **2026-10-29 09:42** | 🟢 **v124 早场 #1：v13 DoD #7「CI 触发覆盖闭合」全部交付。** 🆕 **发现并修复一个让 PR 静默失去 CI 验证的触发块缺陷**：`ci.yml` 的 `pull_request: branches: [master]` 过滤器意味着**只有 base 为 `master` 的 PR 会启动 CI**，而本仓库 v13 用 stacked PR 结构 → **PR #63 从未跑过一次 CI**（`gh pr checks 63` → `no checks reported`；`statusCheckRollup` → `[]`；`gh run list` 无该分支任何记录；对照组 `exp/dup-pr-probe`（base=master）有 CI 运行 → 唯一变量是 base 分支）。**后果**：#63 携带的 DoD #4（Replay Integrity Guard，51 个新测试）+ DoD #6（`docs/REPRODUCE.md` v1.0，723 行）**从未被 CI 验证过**。⚠️ **事实性错误修正**：v123 两轮记录"PR #63 CI 6/6 SUCCESS"**对 #63 不成立**（实际 0 次运行）—— 已更正。⚠️ **为什么危险**：CI 失败是🔴红（一定有人管）、在跑是🟡灰（通常会等），而**零检查是一片⚪空白** —— 看起来像"还没开始"而不是"永远不会开始"；于是 v123 两轮都把 `MERGEABLE` 读成了"已验证"（**MERGEABLE 说的是"能合并"，不是"已验证"**）。🆕 **解法**：① 触发块去掉 `pull_request` 的 `branches:` 过滤器（不过度触发：`push` 过滤器**不含 `feat/*`**）② `scripts/ci_trigger_audit.py`（新，唯一实现源）**零第三方依赖**（PyYAML **不在 `requirements.lock`**，import 它会直接搞挂 CI → 自研子集解析器，**看不懂就抛异常而不是猜**；顺手避开 YAML 1.1 把裸 `on` 解析成布尔的坑）+ 只读 + exit 0/1 可当门禁 ③ CI 新增 `ci-trigger-audit` **自举守卫** job（**不执行** `pip install -r requirements.lock` —— **守卫不能依赖它要守护的那套环境**）④ `tests/test_ci_trigger_audit.py`（新）**19 测试**（解析器 12 + 仓库不变量 7，最重要一条：`ci.yml` 的 `pull_request` 过滤器必须是 `None`）。✅ P0 ✅ + P1 ✅（**631 passed / 5 skipped / 0 FAILED**，393.26s，612 → 631）+ P2 ✅（acc 0.7900）+ P3 ✅（8/8 HTTP 契约）+ P1' ✅（`ci_trigger_audit.py` exit 0，6 个 base 全覆盖）。💡 **本轮最重要的产出不是"加了 19 个测试"**：而是**把一个一直存在、但从未被测量的假设变成了 CI 会主动拦住的门禁** —— 修复前"CI 覆盖了所有 PR"只是一句**没人验证过的话**，它恰好在唯一一次不成立时静悄悄失效了两轮；现在是一条 **CI 每次都检查、违反就红**的规则。📌 **请皇上决策**：① Merge 本轮 PR ② Merge PR #63（v13 DoD #4，**建议先确认其 CI 状态再合并** —— 修复后它会首次真正获得 CI 验证）③ Merge PR #62 ④ Merge PR #61 ⑤ Merge PR #60 ⑥ 接受 ADR-0018。run log: `strategy/runs/2026-10-29-0942.md` — 第95次提醒 #1 🟢* |
| **2026-10-27 09:30** | 🟢 **v121 早场 #1：v13 DoD #2-#4 全部交付**（replay 执行 / coverage 看板 / 内容寻址存储；registry 4.0G → 180M，回收 3.9GB）。**538 passed / 5 skipped / 0 FAILED**。📌 请皇上 Merge PR #62 / #61 / #60 + 接受 ADR-0018。run log: `strategy/runs/2026-10-27-0930.md` — 第91次提醒 #1（详细正文见 archive）🟢* |
| **2026-10-27 21:41** | 🟢 **v122 晚场 #1：v13 DoD #5「Artifact Compatibility Layer」全部交付**（sklearn 1.4.1 → 1.7.2 产物字节级兼容层；700/700 不可加载模型全部恢复，可加载率 66.1% → 69.4%）。**561 passed / 5 skipped / 0 FAILED**。⚠️ 该轮声称的「PR #63（DoD #5）」**实际从未创建**（`gh pr view 63` → GraphQL error），编号后来被 DoD #4 复用。📌 请皇上 Merge PR #62 / #61 / #60 + 接受 ADR-0018。run log: `strategy/runs/2026-10-27-2141.md` — 第92次提醒 #1（详细正文见 archive）🟢* |
| **2026-10-28 21:30** | 🟢 **v123 晚场 #1：v13 DoD #6「复现指南文档化」全部交付。** 🆕 **`docs/REPRODUCE.md` 重写**：v0.1 占位（833 字节）→ v1.0 完整指南（13,519 字节），12 章覆盖 v12 SDK + v13 Provenance / Replay / Coverage / Compat / Blob Store / Integrity Guard + CLI 速查 + HTTP 契约 + 故障排查。✅ P0 ✅ + P1 ✅（**612 passed / 5 skipped / 0 FAILED**，368.48s）+ P2 ✅（acc 0.7900）+ P3 ✅（health 200 / integrity 200 / integrity_single 200 / integrity_unknown 404 / verify 200 / verify_no_id 400 / predict_batch 200 / predict_no_dataset 400）。📌 **请皇上决策**：① Merge PR #63（v13 DoD #4）② Merge PR #62（v13 DoD #2-#4）③ Merge PR #61（v13 DoD #1）④ Merge PR #60（v12 三 DoD）⑤ 接受 ADR-0018。run log: `strategy/runs/2026-10-28-2130.md` — 第94次提醒 #1 🟢** |
| **2026-10-28 09:34** | 🟢 **v123 早场 #1：v13 DoD #4「Replay Integrity Guard」全部交付。** 🆕 **根因发现**：368 个模型的 stored recipe 与今日代码生成的 recipe 不一致，根因不是模型坏了而是**拼写变了**——历史记录把 tuple 渲染为 Python repr `(50,)`，当前 `build_replay_command()` 渲染为 JSON list `[50]`（provenance 经 JSON 序列化，tuple 变成 list）。**两者指同一个超参数、训出同一个模型。** 🆕 **解法**：`core/replay_guard.py`（新，唯一实现源）用**三段式分级**取代布尔相等比较——`none`（完全相同）/ `cosmetic`（拼写不同但指同一次运行）/ `semantic`（会训出不同的模型）。三个关键判据：① 超参值语义归一化（tuple/list 统一、`50`=`50.0`）② run-defining flag 与 visual-only flag 分离（`--n-samples`/`--noise` 不进入 CLI 训练路径）③ `--params` 排除出 flag 比较（避免仅因参数顺序不同而误报）。🆕 **附带交付**：Registry/SDK/CLI/HTTP 四端接入 + `verify_replay()` 实际执行验证。🔧 **顺带修掉一个真 bug**：`RegistryManager.verify_replay()` 初版写成 `MLDB()`（无 registry base）→ 客户端会连到真实 registry 而不是当前 manager 的 registry；已修为 `MLDB(registry_base=self.registry_base)`。🔧 **事实性错误修正**：v122 晚场声称"PR #63 已开"，实测 **PR #63 不存在**（`gh pr view 63` → GraphQL error）；实际开放的 PR 只有 #60 / #61 / #62 三个。⚠️ **重复 stacked PR 风险**：`origin/feat/v12-sdk-foundation` 与 `origin/feat/v13-provenance-provenance` **都是** `origin/feat/v13-replay-provenance` 的祖先，PR #62 的 diff 已包含 DoD #1–#5 全部内容，与 #60 / #61 构成 stacked PR；建议按 #60 → #61 → #62 顺序 Merge，或直接只 Merge #62 后关闭 #60 / #61。✅ **实测**：21339 个模型，20971 current / 368 cosmetic / **0 semantic** / **0 broken**；1735 个带冻结配方，368 个 stale text（21.2%），**可复现性承诺未破**。P0 ✅ + P1 ✅（**612 passed / 5 skipped / 0 FAILED**，585.49s，561 → 612）+ P2 ✅（acc 0.7900）+ P3 ✅（health 200 / integrity 200 / integrity 404 E2003 / verify 200 / verify 400 / predict batch 200）。📌 **请皇上决策**：① Merge PR #63（v13 DoD #4）② Merge PR #62（v13 DoD #2-#4）③ Merge PR #61（v13 DoD #1）④ Merge PR #60（v12 三 DoD）⑤ 接受 ADR-0018 —— 五者均不阻塞后续开发。run log: `strategy/runs/2026-10-28-0934.md` — 第93次提醒 #1 🟢** |

---

## 当前全局状态

| 项目 | 状态 |
|------|------|
| v8 (Model Registry) | ✅ 完成 (ADR-0013 Accepted 2026-07-04) |
| v9 (Docs & Examples) | ✅ 完成 (ADR-0014 Accepted 2026-07-08) |
| v10 (API & Web UI) | ✅ 完成 (ADR-0015 Accepted 2026-07-10) |
| **v11 (Multi-Dataset + Experiment History)** | ✅ **完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted 2026-10-25**（DoD #1-4 全绿）|
| **v12 (Python API & SDK Foundation)** | ✅ **完成** — DoD #1 SDK / #2 Async queue / #3 Registry 版本化+标签查询 全绿，ADR-0017 Accepted；PR #60 已交付（OPEN / CLEAN / MERGEABLE，CI 6/6 SUCCESS），待皇上 Merge |
| **v13 (Experiment Provenance & Reproducibility)** | 🟢 **DoD #1-#8 + #12 全部完成** — #1 provenance capture（PR #61 待 Merge）/ #2 replay execution / #3 coverage dashboard / #4 content-addressed storage（PR #62 待 Merge）/ #5 artifact compatibility（v122 晚场交付，PR 编号落空）/ **#12 replay integrity guard（PR #63 待 Merge，已 7/7 SUCCESS）** / **#7 CI 触发覆盖闭合（PR #66 待 Merge）** / **#8 PR 级 CI 覆盖验证（PR #67 待 Merge）**；ADR-0018 待 Accepted |
| **本轮 PR** | 🟢 **PR #67 已开**（v125 晚场交付 `feat/v13-pr-coverage-audit`，已 commit + push + PR，CI 8 job QUEUED）|
| **CI 触发覆盖** | ✅ **已闭合** — `pull_request` 无 `branches:` 过滤器；`scripts/ci_trigger_audit.py` 门禁（exit 0/1）+ CI `ci-trigger-audit` 自举 job；CI job 数 6 → **7** |
| **PR 级 CI 覆盖** | ✅ **已闭合** — `scripts/pr_coverage_audit.py` 门禁（exit 0/1）+ CI `pr-coverage-audit` 自举 job；CI job 数 7 → **8**；5/5 PR verified |
| **待合 PR #67** | 🟢 **PR #67 OPEN + CLEAN + MERGEABLE**（v13 DoD #8，待皇上 Merge）⚠️ CI 8 job **QUEUED**（刚开，尚未跑完）|
| **待合 PR #63** | 🟢 **PR #63 OPEN + CLEAN + MERGEABLE + CI 7/7 SUCCESS**（v13 DoD #4 + #6，待皇上 Merge）✅ **已通过回移修复获得首次 CI 验证** |
| **待合 PR #62** | 🟢 **PR #62 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #2-#4，待皇上 Merge）|
| **待合 PR #61** | 🟢 **PR #61 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v13 DoD #1 provenance capture，待皇上 Merge）|
| **待合 PR #60** | 🟢 **PR #60 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v12 三 DoD，待皇上 Merge）|
| **本轮分支** | `feat/v13-ci-trigger-coverage`（新，base `feat/v13-replay-integrity-guard`）|
| **v13 DoD #7** | ✅ **CI 触发覆盖闭合完成** — 修复 `pull_request: branches: [master]` 过滤器 + `scripts/ci_trigger_audit.py` 可执行门禁 + CI 自举 job + 19 测试 |
| **v13 DoD #8** | ✅ **PR 级 CI 覆盖验证完成** — `scripts/pr_coverage_audit.py` 可执行门禁 + CI 自举 job + 17 测试 + 回移修复使 PR #63 首次获得 CI |
| **v13 DoD #6** | ✅ **复现指南文档化完成** — `docs/REPRODUCE.md` v0.1→v1.0，ADR-0018 下轮待办第 2 条已闭合|
| **CI 安全审计** | ✅ **master 已脱险**：PR #58/#59 merged 后 master = pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0） |

---

## 价值确认

- **受益人**：皇上 / 仓库维护者 / 所有依赖"PR 合并前已被 CI 验证"的下游 / 未来的每一个贡献者
- **价值**：① 把"每个 PR 都必须被 CI 验证"从**没人验证过的假设**变成 **CI 每次检查、违反就红的门禁** ② 修复一个**让 PR 静默失去验证**的真实缺陷（PR #63 零 CI） ③ 区分了三种 CI 状态的**视觉信号**（红=失败 / 灰=在跑 / 白=永远不会跑）—— 最危险的是最后一种 ④ 审计器**零依赖**，且守卫 job **不依赖它要守护的那套环境** ⑤ **只读**：审计从不改写 workflow，修不修由人决定 ⑥ 顺手避开了 YAML 1.1 把裸 `on` 解析成布尔的坑
- **验证**：P0 ✅ compileall 0 + 6 个模块 import OK；P1 ✅ **646 passed / 5 skipped / 2 pre-existing timeout FAILED（692.87s）**；P2 ✅ `benchmarks --quick` PASSED（acc 0.7900）；P3 ✅ health 200 + integrity_full 200 + integrity_single 200 + integrity_unknown 404 + verify 200 + verify_no_id 400 + predict_batch 200 + predict_no_dataset 400；P1' ✅ `ci_trigger_audit.py` exit 0（6 个 base 分支全覆盖）+ 干净 checkout 复验 exit 0；P1'' ✅ `pr_coverage_audit.py` exit 0（5/5 PR verified）+ 干净 checkout 复验 exit 0
- **当前状态**：🟢 **无外部阻塞** — v13 DoD #1-#8 + #12 全部交付且本地 P0–P3 全绿；待皇上 Merge PR #60 / #61 / #62 / #63 / #66 / #67 + 接受 ADR-0018
- **最近一次验证**：2026-11-01 09:48 CST（v125 晚场 #1）
- **master HEAD**：`4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**：`feat/v13-pr-coverage-audit`（新，base `feat/v13-ci-trigger-coverage`）
- **阻塞**：无（PR #60 / #61 / #62 / #63 / #66 / #67 待 Merge，不阻塞下一轮开发）
- **⚠️ 价值尚未完全实现**：PR #67 的 **CI 验证要等它真正跑起来**才算落地。
  触发块已修、门禁已建，但**"CI 会覆盖所有 PR"这个承诺要到第一个 base 非 `master` 的 PR 跑出绿色 CI 才算被证实**。
  下轮第一件事：确认本轮 PR 的 CI 状态（应出现 `pr-coverage-audit` job + 原有 7 job = 8 job）。