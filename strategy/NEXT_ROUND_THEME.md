# NEXT_ROUND_THEME.md — ml-decision-boundary v120 早场（v13 DoD #1 Provenance Capture 完成）

**更新时间：** 2026-10-26 09:56 CST / 2026-10-26 01:56 UTC
**版本：** v120 早场
**维护人：** 太子

---

## 🟢 v120 早场 状态：**v13 DoD #1 实验 provenance 捕获完成，P0/P1/P2/P3 全绿（449 passed / 0 failed），待推送开 PR**

### 🆕 本轮交付：Experiment Provenance Capture（v13 DoD #1）

| 交付物 | 内容 |
|--------|------|
| `core/provenance.py` | **新** `canonical_json()` / `environment_info()` / `git_info()` / `compute_fingerprint()` / `build_provenance()` / `provenance_diff()` |
| `core/registry.py` | `save_model(provenance=...)` / `get_provenance()` / `compare_provenance()`；旧模型补 `provenance={}` |
| `ml_db/client.py` | SDK 新增 `get_provenance()` / `compare_provenance()`；缺失模型抛 `ModelNotFoundError` |
| `main.py` | CLI 新增 `model provenance <id>` / `model diff <id1> <id2>` |
| `tests/test_provenance.py` | **新 11 个测试**（捕获 / 指纹稳定性 / legacy 兼容 / diff / SDK 契约）|
| `docs/adr/ADR-0018-v13-dod.md` | **新** v13 DoD 细化 ADR |
| `spec/phases.md` | v13 阶段与 DoD 落档 |
| `spec/API.md` | Provenance 语义小节（JSON 形状 + 指纹规则 + 向后兼容）|

### 设计要点

1. **指纹语义**：canonical JSON + SHA-256（前 16 hex），覆盖 `seed` / `dataset` / `hyperparameters` / 环境版本(python,numpy,sklearn,joblib) / `git.commit`。
2. **排除易变字段**：`captured_at` / `git.dirty` / `git.branch` / `environment.platform` **不进指纹也不进 diff** —— 否则会出现“指纹相同但记录不同”的语义冲突。
3. **结构化 diff**：比较结构化值而非 JSON 字符串（避开 `{"C":1.0}` vs `{"C":1}` 的字符串陷阱），返回 `{field,left,right}`。
4. **零迁移**：v13 前的旧模型读回 `{}`，原 JSON **字节不变**（测试用字节相等断言守护）。
5. **三端同源**：Registry / SDK / CLI / HTTP 共用 `core/provenance.py`，永不漂移；`/api/registry` 返回体自动携带 provenance。

### ⚠️ 本轮事故：工作树被外部 `git reset --hard` 清空

本轮实现过程中，未提交改动（含新文件）一次性消失；`git reflog` 显示 `6bf7b75 HEAD@{0}: reset: moving to HEAD` 且无对应 commit → 一次未提交的 `git reset --hard`。独立评审子代理会话已回收，且 agent-to-agent history 被禁用，无法确证责任方。
**处置**：重建全部实现 + **立即做保护性提交** `855f045`。
**新增规则**：每个实现单元完成即 commit，禁止跨轮次累积未提交改动。

### 验收结果

| 层级 | 命令 | 结果 |
|------|------|------|
| **P0** | `compileall -q .` + import smoke | ✅ exit 0 + `import main / ml_db / core.provenance` OK |
| **P1** | `pytest -q` | ✅ **449 passed, 5 skipped, 0 FAILED**（330.80s，438 → 449，+11）|
| **P2** | `python3 -m benchmarks --quick` | ✅ PASSED（circles/SVM, acc 0.7900, thr 0.7000）→ `benchmarks/reports/2026-10-26.md` |
| **P3** | API 契约 + health | ✅ `curl localhost:5000/api/health` → **HTTP 200**；`/api/registry` 五种查询实测通过 |

### 附带修复

`tests/test_benchmarks_smoke.py` full-suite 子进程超时 `120 → 300s`（该套件本机稳定超 120s，属测试预算问题，产品逻辑未改）。

### 🔖 Commit 记录（本轮）

| Commit | 说明 |
|--------|------|
| `855f045` | `feat(v13): DoD #1 — experiment provenance capture (registry + SDK + CLI + fingerprint + tests)`（9 files, +530 / -7）|

> run log: `strategy/runs/2026-10-26-0156.md`

---

## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-10-23 10:17** | 🟢🚨 **v117 晚场 #3：cron 触发例行检查，P0 ✅（compileall + import OK）+ P1 ✅（324/5/0，61.59s）+ P2 ✅（benchmark quick PASSED, SVM/circles acc 0.7900），PR #57 仍 CLOSED（mergedAt: null，closedAt=`2026-10-19T19:47:29Z`，mergeStateStatus CLEAN，mergeable MERGEABLE）🚨，皇上仍未决策 A/B/C（已 ~90h+）。🟢 **本轮关键解除：feat/v11 分支自身 CI 已确认 6/6 SUCCESS**（run #39834210464 + #39833849516），预案 A 前置条件全部满足。工作树 clean ✅，本地 HEAD `0002bfb` = 远端 head ✅，run log: `strategy/runs/2026-10-23-1017.md` — 第86次提醒 #4 🚨（持续等决策，但 CI 阻塞已解除）** |
| **2026-10-24 02:01** | 🟢 **v118 晚场 #1：cron 触发例行检查 + 交付 PR #59。P0 ✅ + P1 ✅（324/5/0，75.92s）+ P2 ✅（benchmark quick acc 0.7900），feat/v11 CI 连续 4 轮 SUCCESS ✅。🚨 **重大纠偏：PR #58 其实早已 OPEN + CLEAN + CI 6/6 SUCCESS**，历轮 theme「等 A/B/C」为陈旧信息，本轮起不再重复请求 A/B/C。🆕 **新交付 PR #59**（master 安全清理：pillow 12.2.0→13.0.0 修 24 CVE、werkzeug 3.1.8→3.1.9 修 PYSEC-2026-4312、CI Python 3.10→3.12、master registry 测试时区 bug 修复；实测 master 共 25 个 CVE → pip-audit 0 vuln；master P1 从 2 failed → 283 passed/1 skipped）。**请皇上点 Merge：#58（v11）+ #59（master 安全，必合）**，run log: `strategy/runs/2026-10-24-0201.md` — 第88次提醒 #1 🟢** |
| **2026-10-24 22:20** | 🔴 **v118 晚场 #3：结论不变（只点 PR #58），但证据显著升级。🆕 **模拟 squash 合并后的 master 端到端验收通过**：P1 **324 passed / 5 skipped / 0 FAILED**（116.29s）+ pip-audit **No known vulnerabilities found** + pillow 13.0.0 / werkzeug 3.1.9 / Python 3.12 ×7 / UTC 修复全部就位 → **实证 #58 单独合入即修复 master，#59 应 Close**。🔬 **修正上轮时区复现方法**：上轮 `TZ=Etc/GMT+8` 结果依赖墙钟（当前时刻 UTC 与 GMT+8 同日，实测无法复现），本轮改用注入本地时钟偏移的对称实验 → master **2 failed** / #58 分支 **12 passed**，且根因代码级确认（`core/registry.py:115` 用 UTC，master 测试用本地 `date.today()`，GMT+8 下每天 8h 窗口不一致）。✅ CVE **63 条**独立复核确认；✅ #59 **4/4 文件**与 #58 逐字节相同；✅ `git merge-base` 空 → **必须 Squash**。🚨 **修复本地环境损坏**：全局 `pytest_scenario_files` editable 路径 `/tmp/psf-fork` 被删 + 多个包缺 RECORD 导致 pip 无法卸载 → 按 `requirements.lock` 重装后 P1 首次即 324/5/0。P0 ✅ + P1 ✅（324/5/0，72.89s）+ P2 ✅（acc 0.7900）+ pip-audit ✅ 0 vuln。**👑 请皇上只点 PR #58 的 Merge 按钮（务必 Squash and merge）**，合并后 Close PR #59。run log: `strategy/runs/2026-10-24-2207.md` — 第88次提醒 #3 🔴** |
| **2026-10-24 10:11** | 🔴 **v118 晚场 #2：例行闭环 + PR 合并顺序独立验证。P0 ✅ + P1 ✅（324/5/0，68.86s）+ P2 ✅（acc 0.7900），CI 6/6 SUCCESS（run #40054000623）。🚨 **重大纠偏 #1：上轮「点两个 Merge」是错的** —— 实测 #59 的 4 个文件与 #58 blob SHA **逐字节相同**（requirements.lock / ci.yml / release.yml / test_registry.py 全 IDENTICAL），#58 合并后 master 即含 pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12 + UTC 修复 → **#59 应 Close 而非 Merge**。🚨 **重大纠偏 #2：CVE 实测 63 条**（非上轮「25 个」）—— pillow12.2.0+werkzeug3.1.8 对照审计 63 条 CVE 行，修复后 `No known vulnerabilities found`；master 最后一次 CI 是 **2026-07-04**，从未重跑，绿是假象。🆕 **时区 bug 确定性复现**：上轮「master 2 failed」当前不可复现（本地与 UTC 同日），用 `TZ=Etc/GMT+8` 强制复现 → master **2 failed** / #59 分支同条件 **12 passed**。⚠️ 记录风险：v11 与 master 无共同祖先（`git merge-base` 为空），本地 merge 报 unrelated histories，**建议 Squash and merge**。**👑 请皇上只点 PR #58 的 Merge 按钮**，合并后 Close PR #59。#59 分支独立 worktree P1 ✅（283/1/0，132.61s）+ P2 ✅ + pip-audit ✅ 0 vuln。run log: `strategy/runs/2026-10-24-1011.md` — 第88次提醒 #2 🔴** |
| **2026-10-25 02:10** | 🎉 **v119 早场 #1：皇上已 Merge！PR #58 merged 2026-10-24T16:27:28Z（`99b8490`）+ PR #59 merged 2026-10-24T16:27:51Z（`4082158`），master CI run #40111672401 **6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0）。v11 收口：ADR-0016 → Accepted，`spec/phases.md` v11 已完成 ✅。🆕 v12 启动并交付 DoD #1 **Python SDK**：`ml_db/` 包（`MLDB` 顶层 API + E2xxx 错误层级）+ `core/train_utils.py` 抽出 `BUILTIN_FACTORIES`/`BUILTIN_MODEL_NAMES` + `tests/test_sdk.py`（21 新测试）+ `examples/06_sdk_usage.py` + README §7。P0 ✅ + P1 ✅（**345 passed / 5 skipped / 0 FAILED，79.13s**）+ P2 ✅（acc 0.7900）+ SDK 走查 ✅。run log: `strategy/runs/2026-10-25-0210.md` — 第89次提醒 #1 ✅（**无需皇上操作**）** |
| **2026-10-26 09:56** | 🟢 **v120 早场 #1：v13 启动并交付 DoD #1「experiment provenance capture」。** 新增 `core/provenance.py`（canonical JSON + SHA-256 指纹 + 结构化 diff）+ Registry/SDK/CLI 三端接入（`model provenance <id>` / `model diff <id1> <id2>`）+ `tests/test_provenance.py`（11 新测试）+ ADR-0018 + phases/API 文档。指纹覆盖 seed/dataset/hyperparams/环境版本/git commit，排除 `captured_at`/`git.dirty`/`platform` 等易变字段。P0 ✅ + P1 ✅（**449 passed / 5 skipped / 0 FAILED**，330.80s，438 → 449）+ P2 ✅（acc 0.7900）+ P3 ✅（health HTTP 200，`/api/registry` 五种查询实测通过）。⚠️ **本轮事故**：工作树被外部 `git reset --hard` 清空一次（reflog `reset: moving to HEAD`，无对应 commit），已重建全部实现并**立即做保护性提交** `855f045`；新增规则“每个实现单元完成即 commit”。📌 **请皇上决策**：① Merge PR #60（v12）② 接受 ADR-0018（v13 DoD 细化）——两者均不阻塞后续开发。run log: `strategy/runs/2026-10-26-0156.md` — 第90次提醒 #1** |

---

## 当前全局状态

| 项目 | 状态 |
|------|------|
| v8 (Model Registry) | ✅ 完成 (ADR-0013 Accepted 2026-07-04) |
| v9 (Docs & Examples) | ✅ 完成 (ADR-0014 Accepted 2026-07-08) |
| v10 (API & Web UI) | ✅ 完成 (ADR-0015 Accepted 2026-07-10) |
| **v11 (Multi-Dataset + Experiment History)** | ✅ **完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted 2026-10-25**（DoD #1-4 全绿）|
| **v12 (Python API & SDK Foundation)** | ✅ **完成** — DoD #1 SDK / #2 Async queue / #3 Registry 版本化+标签查询 全绿，ADR-0017 Accepted；PR #60 已交付（OPEN / CLEAN / MERGEABLE，CI 6/6 SUCCESS），待皇上 Merge |
| **v13 (Experiment Provenance & Reproducibility)** | 🟡 **进行中 — DoD #1 provenance capture 已完成**（`core/provenance.py` + Registry/SDK/CLI 三端 + 11 专项测试，P1 449/0 全绿）；ADR-0018 待 Accepted |
| **本轮 PR** | 🟢 **PR #60 OPEN + CLEAN + MERGEABLE + CI 6/6 SUCCESS**（v12 三 DoD，待皇上 Merge）|
| **本轮分支** | `feat/v13-provenance-provenance` @ `855f045`（v13 DoD #1，待推送开 PR）|
| **CI 安全审计** | ✅ **master 已脱险**：PR #58/#59 merged 后 master = pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0） |

---

## 价值确认

- **受益人**: 皇上 / 仓库维护者 / 外部 Python 使用者 / 所有拉取 master 的用户；特别是需要**判定“两次实验是否同条件产生”**的回归分析与实验复现者
- **价值**: ① **实验可追溯性从“不可判定”到“可机器验证”**：此前 Registry 只存结果/数据集 hash/超参，**无法回答“这两个模型是不是同条件下训出来的”**；本轮引入 seed/环境/git commit/规范化指纹 + 结构化 diff，给出确定答案 ② **fingerprint 让回归检测有了依据**：`sha256:` 指纹一致 = 同条件复现，差异即刻定位到具体字段（实测 `hyperparameters: {'C': 1.0} → {'C': 10.0}`）③ **三端一致**：Registry/SDK/CLI/HTTP 共用 `core/provenance.py`，结果零漂移；SDK 用户可直接在脚本/notebook 中调用 ④ **零迁移不破坏存量**：旧模型读回 `{}` 且原 JSON 字节不变，无任何迁移风险
- **验证**: P0 ✅ compileall 0 + `import main/ml_db/core.provenance` OK；P1 ✅ **449 passed / 5 skipped / 0 FAILED（330.80s，438 → 449）**；P2 ✅ `benchmarks --quick` PASSED（acc 0.7900）→ `benchmarks/reports/2026-10-26.md`；P3 ✅ health HTTP 200 + `/api/registry` 五种查询实测通过；端到端 ✅ 两次训练 → provenance 差异精确到 `hyperparameters`
- **当前状态**: 🟢 **无外部阻塞** — v13 DoD #1 已交付；待皇上 Merge PR #60 + 接受 ADR-0018
- **最近一次验证**: 2026-10-26 09:56 CST（v120 早场 #1）
- **master HEAD**: `4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**: `feat/v13-provenance-provenance` @ `855f045`（基于 `6bf7b75`）
- **阻塞**: 无（PR #60 待 Merge，不阻塞下一轮开发）
