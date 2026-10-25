# NEXT_ROUND_THEME.md — ml-decision-boundary v119 晚场（v12 DoD #3 + ADR-0017 Accepted）

**更新时间：** 2026-10-25 21:50 CST / 2026-10-25 13:50 UTC
**版本：** v119 晚场
**维护人：** 太子

---

## 🟢 v119 晚场 状态：**v12 DoD #3 Registry 改进完成，ADR-0017 Accepted，PR #60 已更新，CI 6/6 SUCCESS**

### 🆕 本轮交付：Registry 改进（v12 DoD #3）

| 交付物 | 内容 |
|--------|------|
| `core/registry.py` | `family_key()` / `_next_version()` / `list_model_families()` / `get_model_versions()` / `get_latest_version()` / `list_models_by_tags()` / `tag_index()` / `_normalize()` |
| `ml_db/client.py` | SDK 新增 `list_models_by_tags()` / `tag_index()` / `list_model_families()` / `get_model_versions()` / `get_latest_version()` |
| `main.py` | CLI 新增 `model list --tags A B --match any\|all`、`model versions <id>`、`model families`；`list`/`inspect` 增加 VER 列 |
| `api/registry.py` | **新** Vercel serverless `GET /api/registry`（单模型 / 版本 / 家族 / 批量标签）|
| `web/server.py` | 本地 Flask 新增 `/api/registry` + `/api/health` 别名（与 serverless 同契约）|
| `tests/test_registry_versioning.py` | **58 个新测试**（family key / 版本化 / 旧数据兼容 / 批量标签 / SDK / API 契约 / 双实现 parity）|
| `spec/API.md` | **新** HTTP API 契约文档（P3 要求）|

### 设计要点

1. **family key** = `model_type|dataset_name|<sorted hyperparameters>` —— 超参键字典序排序 + 值 `repr` 渲染，故 `{"C":1.0}` 与 `{"C":1}` 属不同 family（可能训练出不同结果）。
2. **版本递增**：同 family 重新训练 → `v1 → v2 → v3 ...`；不同 family 各自从 `v1` 开始。
3. **零迁移向后兼容**：v12 之前的元数据 JSON **不重写**，读取时由 `_normalize()` 动态补齐 `version=1` + 派生 `family`；模型 ID 格式（`YYYY-MM-DD_<6hex>`）完全不变。
4. **批量标签语义**：`mode="any"` = 并集（至少命中一个）、`mode="all"` = 交集（必须全部命中）；结果按 `created_at` 降序。空标签列表 / 非法 mode → `ValueError`。
5. **三端同源**：Registry / SDK / CLI / HTTP 共享同一 `core/registry.py` 逻辑，结果永不漂移。

### 🔍 本地 review 修复（独立子代理 review + 自查）

| # | 问题 | 修复 |
|---|------|------|
| 1 | `tag_model()` / `untag_model()` 走 `get_metadata()`（已规范化）→ 给旧模型打标签会把派生的 `version`/`family` **写入旧 JSON**，违反“不重写旧文件”约束 | 新增 `_read_raw_metadata()`；打/去标签只读原始元数据、只写回 `tags` 字段 → 旧文件形状不变 |
| 2 | `tag_index()` 与 `list_tags()` 实现完全重复，且 docstring 声称 “Unlike list_tags…”（与事实不符） | `tag_index()` 作为唯一实现，`list_tags()` 改为委托（向后兼容不变）|
| 3 | `?tags=`（显式传空串）静默返回全量列表 —— 与 spec 声明的 400 不符 | 两端改为 `if tags_arg is not None:` → 解析后为空一律 400 |
| 4 | serverless 与 Flask 两实现缺少一致性约束 | 新增 `TestRegistryAPIContractParity`（参数化 7 组用例比对状态码与响应键）|
| 5 | `_legacy_family()` 对 `dataset` 为字符串 / `hyperparameters` 为 `None` 的畸形旧数据会抛 `AttributeError` | 改为类型安全取值（`isinstance` 判定）|
| 6 | CLI / SDK / Flask 各自硬编码 registry 根，无法对 scratch registry 做端到端验证 | 统一支持 `MLDB_REGISTRY_BASE` 环境变量（`get_registry_manager()` / `MLDB()` / Flask 路由）|

### 验收结果

| 层级 | 命令 | 结果 |
|------|------|------|
| **P0** | `compileall -q .` + import smoke | ✅ exit 0 + `import main` OK |
| **P1** | `pytest -q` | ✅ **438 passed, 5 skipped, 0 FAILED**（140.95s，424 → 438，+14）|
| **P2** | `benchmarks/run.py --quick` | ✅ PASSED（circles/SVM, acc 0.7900, thr 0.7000）→ `benchmarks/reports/2026-10-25.md` |
| **P3** | API 契约 + health | ✅ `spec/API.md` 新建 + `curl localhost:5000/api/health` → **HTTP 200**；`/api/registry` 7 组参数用例状态码与 spec 一致（200/200/200/200/400/400/404）|
| **CI** | GitHub Actions | ✅ run `40201496276` **6/6 SUCCESS**（benchmark / depth-sweep / hyperparam-sweep / security-audit / quality-checks / quality-gates）|

### 🔗 PR #60

| 项目 | 状态 |
|------|------|
| PR #60 | **OPEN · 本轮已更新**（未 merge）|
| 标题 | `feat(v12): SDK Foundation — DoD #1 SDK / #2 Async training / #3 Registry 版本化 + 标签批量查询` |
| Base | `master` (`4082158`) |
| Head | `feat/v12-sdk-foundation` @ `ef78b9c` |
| 合并态 | `mergeable=MERGEABLE` · `mergeStateStatus=CLEAN` |
| URL | https://github.com/Jah-yee/ml-decision-boundary/pull/60 |

### 🔖 Commit 记录（本轮）

| Commit | 说明 |
|--------|------|
| `ef78b9c` | `feat(v12): DoD #3 — Registry 模型版本化 + 标签批量查询`（11 files, +1451 / -37）|

> **作者邮箱说明**：本轮首次 commit 使用 `jydu_seven@outlook.com` 被 GitHub 拒绝（GH007 —— 私有邮箱保护）。
> 改为仓库既有的 `166608075+Jah-yee@users.noreply.github.com`（同一 `Jah-yee` 账号）后 push 成功。
> 如需统一为 outlook 邮箱，需先在 GitHub → Settings → Emails 将其设为公开。

> **本轮 P1 说明**：首轮全量跑出现过 1 个 `test_benchmarks_full_suite_runs` 失败，经定位为**并发写同一 registry 目录**导致的 flake（review 子代理同时在跑 `pytest -q`）；单跑通过，停并发后全量重跑 **438 passed / 0 failed**。


### ⚠️ 本轮环境修复（非产品代码）

`python-dotenv` 包目录被清空且丢失 `RECORD`（上次 pip 清理遗留）→ Flask 启动报 `AttributeError: module 'dotenv' has no attribute 'find_dotenv'`。
修复：删除空目录 + 残留 dist-info → `pip install --user --break-system-packages python-dotenv==1.2.2` → 服务正常启动。

### 🧭 下一轮（v13 规划）

v12 DoD #1-#4 全部完成，**ADR-0017 已 Accepted** → 可以开始 v13 主题规划。

---


## 皇上操作记录

> ℹ️ 历史轮次正文已归档至 `strategy/archive/NEXT_ROUND_THEME_ARCHIVE.md`（本文件保持精简，防止 cron 上下文溢出）

| 日期 | 操作 |
|------|------|
| **2026-10-23 22:12** | 🚨 **v118 早场 #1：cron 触发例行检查，P0 ✅（compileall + import OK, py3.12.3）+ P1 ✅（324/5/0，76.68s）+ P2 ✅（benchmark quick PASSED, acc 0.7900），PR #57 仍 CLOSED（mergedAt: null，closedAt=`2026-10-19T19:47:29Z`，mergeStateStatus CLEAN，mergeable MERGEABLE）🚨，皇上仍未决策 A/B/C（已 ~92h+）。CI **连续 3 轮 SUCCESS**（run #39889110714，HEAD `9d43beb`）✅，工作树 clean ✅，本地 HEAD `9d43beb` = 远端 head ✅，run log: `strategy/runs/2026-10-23-2212.md` — 第87次提醒 #1 🚨（持续等决策）** |
| **2026-10-23 10:17** | 🟢🚨 **v117 晚场 #3：cron 触发例行检查，P0 ✅（compileall + import OK）+ P1 ✅（324/5/0，61.59s）+ P2 ✅（benchmark quick PASSED, SVM/circles acc 0.7900），PR #57 仍 CLOSED（mergedAt: null，closedAt=`2026-10-19T19:47:29Z`，mergeStateStatus CLEAN，mergeable MERGEABLE）🚨，皇上仍未决策 A/B/C（已 ~90h+）。🟢 **本轮关键解除：feat/v11 分支自身 CI 已确认 6/6 SUCCESS**（run #39834210464 + #39833849516），预案 A 前置条件全部满足。工作树 clean ✅，本地 HEAD `0002bfb` = 远端 head ✅，run log: `strategy/runs/2026-10-23-1017.md` — 第86次提醒 #4 🚨（持续等决策，但 CI 阻塞已解除）** |
| **2026-10-24 02:01** | 🟢 **v118 晚场 #1：cron 触发例行检查 + 交付 PR #59。P0 ✅ + P1 ✅（324/5/0，75.92s）+ P2 ✅（benchmark quick acc 0.7900），feat/v11 CI 连续 4 轮 SUCCESS ✅。🚨 **重大纠偏：PR #58 其实早已 OPEN + CLEAN + CI 6/6 SUCCESS**，历轮 theme「等 A/B/C」为陈旧信息，本轮起不再重复请求 A/B/C。🆕 **新交付 PR #59**（master 安全清理：pillow 12.2.0→13.0.0 修 24 CVE、werkzeug 3.1.8→3.1.9 修 PYSEC-2026-4312、CI Python 3.10→3.12、master registry 测试时区 bug 修复；实测 master 共 25 个 CVE → pip-audit 0 vuln；master P1 从 2 failed → 283 passed/1 skipped）。**请皇上点 Merge：#58（v11）+ #59（master 安全，必合）**，run log: `strategy/runs/2026-10-24-0201.md` — 第88次提醒 #1 🟢** |
| **2026-10-24 22:20** | 🔴 **v118 晚场 #3：结论不变（只点 PR #58），但证据显著升级。🆕 **模拟 squash 合并后的 master 端到端验收通过**：P1 **324 passed / 5 skipped / 0 FAILED**（116.29s）+ pip-audit **No known vulnerabilities found** + pillow 13.0.0 / werkzeug 3.1.9 / Python 3.12 ×7 / UTC 修复全部就位 → **实证 #58 单独合入即修复 master，#59 应 Close**。🔬 **修正上轮时区复现方法**：上轮 `TZ=Etc/GMT+8` 结果依赖墙钟（当前时刻 UTC 与 GMT+8 同日，实测无法复现），本轮改用注入本地时钟偏移的对称实验 → master **2 failed** / #58 分支 **12 passed**，且根因代码级确认（`core/registry.py:115` 用 UTC，master 测试用本地 `date.today()`，GMT+8 下每天 8h 窗口不一致）。✅ CVE **63 条**独立复核确认；✅ #59 **4/4 文件**与 #58 逐字节相同；✅ `git merge-base` 空 → **必须 Squash**。🚨 **修复本地环境损坏**：全局 `pytest_scenario_files` editable 路径 `/tmp/psf-fork` 被删 + 多个包缺 RECORD 导致 pip 无法卸载 → 按 `requirements.lock` 重装后 P1 首次即 324/5/0。P0 ✅ + P1 ✅（324/5/0，72.89s）+ P2 ✅（acc 0.7900）+ pip-audit ✅ 0 vuln。**👑 请皇上只点 PR #58 的 Merge 按钮（务必 Squash and merge）**，合并后 Close PR #59。run log: `strategy/runs/2026-10-24-2207.md` — 第88次提醒 #3 🔴** |
| **2026-10-24 10:11** | 🔴 **v118 晚场 #2：例行闭环 + PR 合并顺序独立验证。P0 ✅ + P1 ✅（324/5/0，68.86s）+ P2 ✅（acc 0.7900），CI 6/6 SUCCESS（run #40054000623）。🚨 **重大纠偏 #1：上轮「点两个 Merge」是错的** —— 实测 #59 的 4 个文件与 #58 blob SHA **逐字节相同**（requirements.lock / ci.yml / release.yml / test_registry.py 全 IDENTICAL），#58 合并后 master 即含 pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12 + UTC 修复 → **#59 应 Close 而非 Merge**。🚨 **重大纠偏 #2：CVE 实测 63 条**（非上轮「25 个」）—— pillow12.2.0+werkzeug3.1.8 对照审计 63 条 CVE 行，修复后 `No known vulnerabilities found`；master 最后一次 CI 是 **2026-07-04**，从未重跑，绿是假象。🆕 **时区 bug 确定性复现**：上轮「master 2 failed」当前不可复现（本地与 UTC 同日），用 `TZ=Etc/GMT+8` 强制复现 → master **2 failed** / #59 分支同条件 **12 passed**。⚠️ 记录风险：v11 与 master 无共同祖先（`git merge-base` 为空），本地 merge 报 unrelated histories，**建议 Squash and merge**。**👑 请皇上只点 PR #58 的 Merge 按钮**，合并后 Close PR #59。#59 分支独立 worktree P1 ✅（283/1/0，132.61s）+ P2 ✅ + pip-audit ✅ 0 vuln。run log: `strategy/runs/2026-10-24-1011.md` — 第88次提醒 #2 🔴** |
| **2026-10-25 02:10** | 🎉 **v119 早场 #1：皇上已 Merge！PR #58 merged 2026-10-24T16:27:28Z（`99b8490`）+ PR #59 merged 2026-10-24T16:27:51Z（`4082158`），master CI run #40111672401 **6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0）。v11 收口：ADR-0016 → Accepted，`spec/phases.md` v11 已完成 ✅。🆕 v12 启动并交付 DoD #1 **Python SDK**：`ml_db/` 包（`MLDB` 顶层 API + E2xxx 错误层级）+ `core/train_utils.py` 抽出 `BUILTIN_FACTORIES`/`BUILTIN_MODEL_NAMES` + `tests/test_sdk.py`（21 新测试）+ `examples/06_sdk_usage.py` + README §7。P0 ✅ + P1 ✅（**345 passed / 5 skipped / 0 FAILED，79.13s**）+ P2 ✅（acc 0.7900）+ SDK 走查 ✅。run log: `strategy/runs/2026-10-25-0210.md` — 第89次提醒 #1 ✅（**无需皇上操作**）** |

---

## 当前全局状态

| 项目 | 状态 |
|------|------|
| v8 (Model Registry) | ✅ 完成 (ADR-0013 Accepted 2026-07-04) |
| v9 (Docs & Examples) | ✅ 完成 (ADR-0014 Accepted 2026-07-08) |
| v10 (API & Web UI) | ✅ 完成 (ADR-0015 Accepted 2026-07-10) |
| **v11 (Multi-Dataset + Experiment History)** | ✅ **完成 — PR #58 merged 2026-10-24T16:27:28Z，ADR-0016 Accepted 2026-10-25**（DoD #1-4 全绿）|
| **v12 (Python API & SDK Foundation)** | 🟡 **进行中 — DoD #1 Python SDK 已交付**（`ml_db/` + 21 测试 + example 06 + README）；剩余 #2 异步训练、#3 Registry 版本化、#4 Accepted |
| **本轮 PR** | 🟢 **PR #60 OPEN + MERGEABLE + CI 6/6 SUCCESS**（run `40120289145`，head `0437ed3`）— v12 DoD #1 Python SDK，待皇上 Merge |
| **CI 安全审计** | ✅ **master 已脱险**：PR #58/#59 merged 后 master = pillow 13.0.0 + werkzeug 3.1.9 + Python 3.12；**master CI #40111672401 6/6 SUCCESS**（2026-07-04 以来首次真实重跑，63 CVE → 0） |

---

## 价值确认

- **受益人**: 皇上 / 仓库维护者 / 外部 Python 使用者 / 所有拉取 master 的用户
- **价值**: ① **v11 彻底闭环**（PR #58 merged → ADR-0016 Accepted → phases.md 落档，3.5 个月的等待在本轮终结）② **master 真实变绿**：3.5 个月来第一次 master CI 重跑 6/6 SUCCESS，63 CVE 清零，「绿是假象」不再成立 ③ **v12 首个可交付物诞生**：`from ml_db import MLDB` 顶层 API 把原本只有 CLI/HTTP 的能力开放给 Python 生态（脚本、notebook、流水线）④ **单一事实源纪律**：SDK 只封装 `core/`，不复制训练逻辑，三端结果零漂移
- **验证**: P0 ✅ compileall 0 + `import main` OK + `import ml_db` OK；P1 ✅ **345 passed / 5 skipped / 0 FAILED（79.13s）**（324 → 345，+21 SDK 测试）；P2 ✅ `benchmarks/run.py --quick` PASSED（acc 0.7900, thr 0.7000）；SDK 走查 ✅ `examples/06_sdk_usage.py` 端到端跑通（train→predict→tag→compare）；master CI ✅ **6/6 SUCCESS**（run `40111672401`，head `4082158`）
- **当前状态**: 🟢 **无外部阻塞** — 本轮起不需要皇上任何操作；v12 DoD #2/#3 由太子按轮次推进
- **最近一次验证**: 2026-10-25 02:10 CST（v119 早场 #1）
- **master HEAD**: `4082158`（PR #59 squash），master CI 6/6 SUCCESS
- **本地分支**: `feat/v12-sdk-foundation`（基于 origin/master `4082158`）
- **阻塞**: 无（PR #60 待 Merge，不阻塞下一轮开发）
