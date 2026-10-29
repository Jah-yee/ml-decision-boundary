# ADR-0018 — v13 DoD 细化：Experiment Provenance & Reproducibility

**日期**: 2026-10-26（2026-10-27 追加 DoD #8 / #9 / #11；2026-10-28 追加 DoD #12；2026-10-29 追加 DoD #7）
**状态**: 🟡 Proposed（DoD #1–#9 + #11–#12 实现完成，DoD #7 本轮交付，待 Accepted）
**维护人**: 太子

---

## 背景

v12 Python API & SDK Foundation 的 DoD #1-#4 已全部完成，ADR-0017 已 Accepted，PR #60 已交付且 CI 6/6 SUCCESS。

CHARTER 的工程使命要求“每一次训练都可追溯、可回归测试、可集成到部署流水线”。v12 Registry 已记录模型结果、数据集 hash、超参数与版本族，但缺少训练条件本身：随机种子、完整数据集参数、运行环境、Git commit。v13 聚焦实验 provenance，让两个模型是否“同条件产生”可以被机器验证。

---

## v13 主题

**Experiment Provenance & Reproducibility**

---

## v13 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | Provenance capture | 注册模型时记录 seed / dataset params / resolved hyperparameters / environment / git commit / canonical fingerprint | P1 | ✅ 完成 (855f045) |
| 2 | Provenance compare | SDK + CLI 支持查看 provenance 与比较两个模型的来源差异 | P1 | ✅ 完成 (855f045) |
| 3 | Backward compatibility | v13 前模型无需迁移；读取时返回空 provenance，不重写旧 JSON | P1 | ✅ 完成 (855f045) |
| 4 | Regression verification | 新增专项测试，完整 P0/P1/P2/P3 验收，CI 全绿 | P0 | ✅ 完成 (v123 早场) |
| 5 | Replay recipe | provenance 附带可执行重放方案（SDK 精确片段 + CLI 命令 + 依赖锁定摘要） | P1 | ✅ 完成 (5e7f843) |
| 6 | HTTP provenance API | `GET /api/provenance` 暴露 provenance / diff / replay | P1 | ✅ 完成 (5e7f843) |
| 7 | CI trigger coverage | CI 触发块保证**所有** base 分支的 PR 都被验证 + 可执行门禁（`scripts/ci_trigger_audit.py` + CI 自举 job） | P0 | ✅ 完成 (v124 早场) |
| 7 | Honest replay | CLI 重放命令仅在可精确复现时标记 exact，否则警告并引导使用 SDK | P1 | ✅ 完成 (5e7f843) |
| 8 | Coverage dashboard | 覆盖率看板：哪些模型缺 provenance、哪些不可重放、阻塞原因分组 | P1 | ✅ 完成 (29089b1) |
| 9 | Replay execution | CLI `model replay --run <id>` 实际重跑并输出复现报告（run-equivalent 判定） | P1 | ✅ 完成 (29089b1) |
| 10 | Content-addressed storage | registry 产物去重（SHA-256 寻址 blob store）+ 迁移工具 | P1 | ✅ 完成 (462b7ce) |
| 11 | Artifact compatibility | 跨 scikit-learn 版本的产物向后兼容层 + registry 健康审计 | P1 | ✅ 完成 (v122 晚场) |
| 12 | Replay integrity guard | 冻结的 replay recipe 漂移分级（none / cosmetic / semantic）+ registry 全量审计 + 实际执行验证 | P1 | ✅ 完成 (v123 早场) |

---

## 设计约束

- Provenance 只记录可复现性与诊断所需字段，不保存凭证或环境变量全集。
- Fingerprint 使用 canonical JSON + SHA-256；`captured_at` 与 `git.dirty` 不参与指纹。
- Registry 是事实源，SDK 与 CLI 仅调用同一核心逻辑，避免三端漂移。
- 旧 registry 零迁移：旧文件不重写。
- 不把通用部署托管或 AutoML 纳入范围，遵守 CHARTER Non-Goals。

### DoD #2 补充约束（重放诚实性）

- **重放命令必须诚实**：`main.py --params` 会把 `KEY=VALUE` 强制转为 int/float/bool，其余一律保留为**字符串**。因此 `hidden_layer_sizes=(50,)` 会被当成字符串 `"(50,)"` 传给 sklearn，**静默训练出一个不同的模型**。
- 重放方案提供两条路径：
  - `sdk` — 始终精确的 Python 片段（`MLDB.train(...)`，含 seed / test_size / 原始类型超参）。
  - `cli` — 便捷命令，**仅当**所有超参都能无损往返且 `test_size` 为默认值、`model_type` 属于 CLI 词表时才标记 `exact: true`；否则 `exact: false` + `warnings` 列表。
- 禁止在 CLI 路径声称“精确”而实际会产出不同模型。
- 依赖摘要基于 `requirements.lock` 的 SHA-256；文件缺失时降级为 `unknown` 而非报错。
- 重放判定区分两层：`run_equivalent`（seed / dataset / model_type / hyperparameters 相同，即“训练结果等价”）与 `fingerprint_match`（含 environment / git commit 的完整指纹相同）。前者才是复现性的正确判据。

---

## 验收标准

- [x] Registry 新模型包含完整 provenance JSON
- [x] `MLDB.get_provenance()` / `MLDB.compare_provenance()` 可用
- [x] CLI `model provenance <id>` / `model diff <id1> <id2>` 可用
- [x] 旧模型返回空 provenance 且原 JSON 字节不变
- [x] Fingerprint 对 volatile 字段稳定，对 seed/参数/环境/git 变化敏感
- [x] P0 compileall + import smoke 通过
- [x] P1 pytest 全绿
- [x] P2 benchmark quick 通过（accuracy 0.79 ≥ 0.70）
- [x] P3 API/health 契约保持通过（`/api/health` 200；`/api/registry` 五种查询契约实测通过）

---

## 实现要点

- `core/provenance.py`：唯一实现源。`build_provenance()` 组装记录，`compute_fingerprint()` 用 canonical JSON + SHA-256（前 16 hex）计算指纹。
- 指纹覆盖：seed / dataset / hyperparameters / 环境版本(python, numpy, scikit_learn, joblib) / git commit。
- 指纹不覆盖：`captured_at`、`git.dirty`、`git.branch`、`environment.platform` — 这些是采集上下文而非复现条件，避免“指纹相同但记录不同”的语义冲突。
- `provenance_diff()` 返回结构化差异（`field`/`left`/`right`），不把 JSON 当字符串比较。
- Registry 为事实源：`save_model(provenance=...)`、`get_provenance()`、`compare_provenance()`；旧模型读回空 `{}` 且不重写原 JSON。
- SDK：`MLDB.get_provenance()` / `MLDB.compare_provenance()`，缺失模型抛 `ModelNotFoundError`。
- CLI：`python3 main.py model provenance <id>`、`python3 main.py model diff <id1> <id2>`。
- 附带修复：`tests/test_benchmarks_smoke.py` full-suite 子进程超时 120s → 300s（实测该套件在本机稳定超过 120s，属测试预算问题，非产品缺陷）。

## DoD #2 实现要点

- `core/provenance.py` 新增：
  - `build_replay_command(record)` — 生成 CLI 命令并判定 `exact`；`cli_params_roundtrip_safe()` 负责识别 CLI 无法无损表示的值（tuple / list / dict / None）。
  - `build_replay_plan(record)` — 组装完整方案：`sdk` / `cli` / `dependencies` / `expected`（含原 fingerprint）。
  - `dependency_digest(repo_root)` — 对 `requirements.lock` 求 SHA-256（前 16 hex）+ 统计 pinned 包数；文件缺失时返回 `available: false`。
- `core/registry.py`：注册时把 replay 方案**冻结**进 provenance（`provenance["replay"]`）；`get_replay_plan()` 对 DoD #2 之前注册的模型按需推导，对 v13 之前的模型返回 `available: false` 而非报错，且不重写旧 JSON。
- `ml_db/client.py`：`MLDB.replay_plan()` / `MLDB.replay()`。`replay()` 使用**记录中的 seed**（而非客户端当前 seed，调用后恢复原值），默认 `register=False` 避免污染 registry。
- `api/provenance.py` + `web/server.py`：`GET /api/provenance`，`id`（必填）/ `compare` / `replay` 三种模式；400（缺 id）/ 404（模型不存在）/ 500（其它）三档状态码与 serverless 一致。
- `main.py`：`python3 main.py model replay <id>` 打印 CLI 命令（带 exact 标注与警告）+ 精确 SDK 片段。
- `tests/test_replay.py`：31 个新测试，含对真实 `main.parse_params` 行为的回归锁定（防止未来修改 CLI 解析器后“重放诚实性”静默失效）。

## DoD #3 实现要点（覆盖率看板 + 重放执行）

- `core/coverage.py`（新建，唯一实现源，只读）：
  - `classify_model(model, replay_plan=None)` — 将单个注册模型归类为 4 种状态之一：
    `replayable_exact` / `replayable_sdk` / `provenance_only` / `no_provenance`。
  - `provenance_coverage(models, replay_plans=None)` — 逐模型分类。
  - `coverage_summary(models, replay_plans=None)` — 聚合计数与百分比（`coverage_pct` / `replayable_pct` / `cli_exact_pct`）。
  - `replayability_report(models, replay_plans=None)` — 按“阻塞原因”分组，输出 `{reason, count, models}`，最常见原因在前。
  - `cli_replay_check(model)` — 比对冻结的 replay 快照与当前推导结果，检测快照漂移。
- **分类正确性的关键点**：DoD #1 时期注册的模型有 provenance 但没有冻结的 replay 快照，其方案可**按需推导**。若仅看快照，这些模型会被误判为 `provenance_only`。因此 `RegistryManager.provenance_coverage()` 先为所有带 provenance 的模型解析一次 `get_replay_plan()`（结果缓存于内存，不写回磁盘），使覆盖率与 registry 自身的判定一致。
- **只读保证**：审计全程不重写任何旧 JSON。`tests/test_coverage.py` 以字节比对锁定这一点。
- `core/registry.py`：`RegistryManager.provenance_coverage()` 返回 `{summary, report, models}`。
- `ml_db/client.py`：`MLDB.coverage()` / `MLDB.coverage_summary()`。
- `main.py`：
  - `python3 main.py model coverage` — 覆盖率看板（总数、覆盖率、精确率、状态分布、阻塞原因 Top-N）。
  - `python3 main.py model replay <id> --run` — **实际重跑**该实验，输出 `reproduced` / `fingerprint_match` / accuracy 差异 / run-level 差异；未复现时以退出码 2 结束。
- `api/provenance.py` + `web/server.py`：`GET /api/provenance?coverage=1`（无需 `id`）返回全量审计结果；两套实现镜像同一契约。
- `tests/test_coverage.py`：28 个新测试，覆盖 4 类状态分类、汇总百分比、阻塞原因分组、快照漂移检测、只读保证、CLI/HTTP 契约。

### 实测结果（真实 registry，20713 个模型）

| 指标 | 数值 |
|------|------|
| 模型总数 | 20713 |
| 带 provenance | 1109（5.35%） |
| 可重放 | 1109（5.35%，其中 1032 CLI 精确、77 需走 SDK） |
| 无 provenance（v13 前注册） | 19604 |
| 审计耗时 | ≈1.1s |

> 结论：v13 前注册的 19604 个模型永远不可重放（历史事实，不可追补）；覆盖率提升的唯一路径是**新注册模型默认携带 provenance**（已由 `save_model` 默认行为保证）。

## 下轮待办

1. PR #60 / #61 合并后以 master 为 v13 基线，避免长期分叉。
2. ~~将重放方案导出为独立文档（如 `docs/REPRODUCE.md`），便于离线审计。~~ ✅ v123 晚场已闭合
3. ~~Registry 体积治理（当前 4.0G / 20713 模型），避免磁盘占用无上限增长。~~ ✅ v121 早场已闭合（4.0G → 180M / 内容寻址存储）
4. **合并 stacked PR**：#60 → #61 → #62 → #63 → 本轮 PR，按序合并（GitHub 会自动 rebase 后继 PR）。
   注意 #63 之前的 PR 从未真正跑过 CI（触发块缺陷，DoD #7 已修），**建议合并前先确认 #63 及本轮 PR 的 CI 状态**。
5. **CI 触发块修复的历史补救**：修复后 #63 及其之后的 PR 会**首次**真正获得 CI 验证。
   若合并后发现某个旧 PR 的 CI 暴露了真实问题，需单独跟进。

## DoD #11 实现要点（产物向后兼容层）

### 问题

v13 DoD #4 的内容寻址存储迁移把 registry 从 4.0G 压到 180M，但迁移后逐个加载产物时暴露出一笔历史债务：**700 个模型无法加载**。

上一轮已证明这与迁移无关（直接 `joblib.load(blob)` 同样失败；复制回旧版 per-model 布局用旧代码路径加载，报同样的错）。本轮把根因定位到了**字节级**：

```
AttributeError: Can't get attribute '__pyx_unpickle_CyHalfBinomialLoss'
on <module 'sklearn._loss._loss' ...>
```

这些产物由 sklearn **1.4.1** 序列化，当时 `sklearn._loss._loss` 把损失函数暴露为一个 Cython 内部名 `__pyx_unpickle_CyHalfBinomialLoss`。pickle 的 `STACK_GLOBAL` 操作码把这个名字连同模块路径一起写进了字节流。到 **1.7.2**，同一个类被改名为公开的 `CyHalfBinomialLoss`，旧名消失 —— 于是 pickle 指向了一个不存在的属性，**反序列化直接失败**。

**产物字节本身没有任何问题，坏掉的只是"名字"。**

### 解法

`core/compat.py`（新，唯一实现源）：一张"旧名 → 新名"别名表，在**反序列化时**把旧名挂回模块上。

```python
_ALIASES = (
    ("sklearn._loss._loss", "__pyx_unpickle_CyHalfBinomialLoss", "CyHalfBinomialLoss"),
)
```

`apply_shims()` 在导入时自动执行（`core.registry` 与 `core.blob_store` 都 import 它），幂等、不会重复安装、模块缺失时静默跳过而不抛错。

### 设计约束

- **不改写任何产物字节**：registry 必须如实记录"当时训练出了什么"。shim 只作用于 unpickle 时刻。
- **不改写元数据 JSON**：与 v13 DoD #3 的只读保证一致。
- **不吞掉 `InconsistentVersionWarning`**：该警告是有信息量的 —— 产物是用另一个库版本拟合的，其数值行为不保证一致。**能加载 ≠ 能信任**。需要确定性时应从记录的 provenance 重新训练。
- **只处理 scikit-learn 确实改名过的内部**：不 monkey-patch estimator 行为，不改模型属性。
- 旧名若在当前 sklearn 中本来就能解析（即正在跑产出该产物的版本），shim 自动是 no-op。

### 实测（真实 registry）

| 指标 | 修复前 | 修复后 |
|------|--------|--------|
| 可加载 | 14059 | **14759** |
| 不可加载 | **700** | **0** |
| 元数据记录（从未存过产物） | 6501 | 6501 |
| 总记录数 | 21260 | 21260 |
| 可加载率 | 66.1% | **69.4%** |

**700/700 全部恢复**（`GB` 类型，全部 `GradientBoostingClassifier`）。

因果对照（同一份产物，同一进程）：

```
A. 未 import core.compat -> has legacy: False
   BASELINE FAIL: AttributeError Can't get attribute '__pyx_unpickle_CyHalfBinomialLoss'
B. 已 import core.compat -> has legacy: True
   WITH SHIM: loaded OK -> GradientBoostingClassifier
```

### 附带交付：registry 健康审计

既然"产物能不能读"是一个此前无法回答的问题，就把它变成可查询的：

- `RegistryManager.health_check(sample=None)` — 逐个解析并反序列化，输出三态分类：
  - `loadable` — 反序列化成功；
  - `no_artifact` — 只有元数据、从未存过产物（**不是损坏**，实测 6501 条）；
  - `unloadable` — 产物存在但读不出来（附失败原因分组）。
- `MLDB.health(sample=None)` / `MLDB.compat_shims()` — SDK 端。
- CLI `python3 main.py model health [--sample N]` — 看板输出。
- `core.compat.check_artifact(path)` — 单文件探针，诊断用途，从不抛错、从不改文件。

实测输出：

```
🩺 Registry health — 21260 registered model(s)
============================================================
   ✅ Loadable:      14759  (69.4%)
   📄 Metadata only:  6501  (no artifact was ever stored)
   ❌ Unloadable:     0

   Active compatibility shims:
      sklearn._loss._loss.__pyx_unpickle_CyHalfBinomialLoss  ->  CyHalfBinomialLoss
```

### 遗留（明确不做）

- 6501 条"元数据记录"没有产物。这不是 bug —— 这些记录注册时就没保存模型对象。**无法追补**，除非重新训练。
- `InconsistentVersionWarning` 仍然存在（13981 个产物带此警告）。这是**诚实提示**：产物是用 1.4.1 拟合的，用 1.7.2 加载，数值不保证逐位一致。本层只保证"能读"，不承诺"读出来一定一样"。


---

## DoD #12 — Replay Integrity Guard（v123 早场）

### 问题

DoD #5 把 replay recipe **冻结**进了每个模型的 provenance 记录。冻结只有在"生成 recipe 的代码不会在底下变"的前提下才安全 —— 而它会变。

实测发现：**368 个模型的 stored recipe 与今日代码生成的 recipe 不一致**。看起来像是 368 个模型坏了。

但根因不是模型坏了，而是**拼写变了**：

```
stored: python main.py --model MLP --dataset circles --seed 42 --params 'hidden_layer_sizes=(50,)'
fresh : python main.py --model MLP --dataset circles --seed 42 --params 'hidden_layer_sizes=[50]'
```

历史记录把 tuple 渲染为 Python repr `(50,)`；当前 `build_replay_command()` 渲染为 JSON list `[50]`（因为 provenance 经过了 JSON 序列化，tuple 变成 list）。**两者指同一个超参数、训出同一个模型。**

朴素字符串相等比较**没有能力**区分"拼写变了"和"语义变了"，于是把 368 个完全没坏的模型报成坏了 —— 这会误导运维者去重新训练它们。

同时，`core/coverage.py` 的 `cli_replay_check()` 是个**孤儿函数**：只被 `tests/test_coverage.py` 调用，**没有接入任何 CLI / SDK / API 路径**。也就是说"recipe 还成立吗"这件事，此前**没有任何人问过**。

### 解法

`core/replay_guard.py`（新，唯一实现源）用**三段式分级**取代布尔相等比较：

| 级别 | 含义 | 判据 |
|------|------|------|
| `none` | recipe 与今日代码输出一致 | 字符串完全相同 |
| `cosmetic` | 拼写不同，**指同一次运行** | 超参值语义等价 + run-defining flag 相同 |
| `semantic` | **会训出不同的模型** | 超参值不同 或 run-defining flag 不同 |

三个判据：

1. **超参值语义归一化** —— `(50,)` 与 `[50]` 归一为同一 tuple；`50` 与 `50.0` 归一为同一数值。序列统一归一为 tuple，不论原写作 tuple 还是 list。
2. **run-defining flag 与 visual-only flag 分离** —— `--n-samples` / `--noise` **不进入 CLI 训练路径**（`main.run_experiment` 硬编码 `n_samples=500, noise=0.3`，这两个 flag 只喂给绘图），因此二者不同是 cosmetic 而非 semantic。
3. **`--params` 排除出 flag 比较** —— 它是可重复 flag，值已由超参映射单独比较；纳入 flag 比较会导致"仅因参数顺序不同"而误报。

### 接线

| 层 | 接口 |
|----|------|
| Registry | `RegistryManager.replay_integrity()` / `recipe_drift(model_id)` / `verify_replay(model_id)` |
| SDK | `MLDB.replay_integrity()` / `recipe_drift(model_id)` / `verify_replay(model_id)` |
| CLI | `python3 main.py model integrity` / `python3 main.py model verify <id>` |
| HTTP | `GET /api/provenance?integrity=1` / `GET /api/provenance?verify=1&id=<id>` |

`verify_replay()` **实际执行** replay 并给出 verdict —— 漂移审计说"recipe 是否还匹配代码"，只有执行才说"运行是否还复现"。这是 DoD #4 "regression verification" 的另一半。

### 实测（真实 registry）

```
🧭 Replay integrity — 21339 registered model(s)
============================================================
   ✅ Recipe current:     20971
   🟡 Cosmetic drift:       368  (spelled differently, same run)
   ❌ Semantic drift:         0  (would reproduce a different model)

   Models with a frozen recipe: 1735 / 21339
   Stale text:  368  (21.2% of recipes)
   Broken:      0  (reproducibility actually lost)
```

**registry 的可复现性承诺目前没有破。** 368 个 stale recipe 全部只是拼写差异，语义未变。

本轮最有价值的产出正是这一点：把一个"看起来 368 个模型坏了"的告警，变成"**0 个模型真的坏了**，368 个只是拼写差异"—— 避免了 368 次无意义重训。

### 分级器的灵敏度（双向验证）

分级器**不是**"一味宽松"。测试同时钉住两个方向：

- **必须报警**（判 `semantic`）：换 dataset / 换 seed / 换 model 类型 / 换超参值 / 加超参 / 删超参 / 序列内容变化（`(50,)` → `(100,)`）—— 7 类全部正确报警；
- **必须不报警**（判 `cosmetic`）：tuple vs list / `C=1` vs `C=1.0` / `--n-samples`+`--noise` 差异 / `--params` 顺序差异 —— 4 类全部正确放行。

### 设计约束

- 审计**只读**：不重写任何元数据字节，不做隐式迁移。旧 registry 零迁移原则不变。
- Registry 是事实源；Registry / SDK / CLI / HTTP 四端调用同一份 `core/replay_guard.py`，不复制判定逻辑。
- 漂移分级只回答"**指同一次运行吗**"，不回答"**训出的模型逐位相同吗**" —— 后者由 `verify_replay()` 实际执行给出。

---

## DoD #7 — CI 触发覆盖闭合（v124 早场）

### 问题

**"每个 PR 都必须被 CI 验证过"—— 这条不变量其实从来没有被强制过。**

`ci.yml` 的触发块是：

```yaml
on:
  push:
    branches: [master, daily/*, fix/*, feature/*]
  pull_request:
    branches: [master]
```

`pull_request` 上的 `branches: [master]` 过滤器意味着：**只有以 `master` 为 base 的 PR 才会启动 CI**。

而本仓库 v13 采用了 **stacked PR** 结构（一个 PR 的 base 是另一个 feature 分支，而不是 `master`）：

| PR | base | CI 运行？ |
|----|------|----------|
| #60 | `master` | ✅ 6/6 SUCCESS |
| #61 | `master` | ✅ 6/6 SUCCESS |
| #62 | `master` | ✅ 6/6 SUCCESS |
| **#63** | **`feat/v13-replay-provenance`** | ❌ **零次 CI 运行** |

实测证据（`gh run list` 全部历史）：

```
2026-10-27 | pull_request | feat/v13-replay-provenance  | success
2026-10-26 | pull_request | feat/v13-provenance-provenance | success
2026-10-25 | pull_request | feat/v12-sdk-foundation     | success
（feat/v13-replay-integrity-guard —— 无任何记录）
```

`gh pr checks 63` → `no checks reported on the 'feat/v13-replay-integrity-guard' branch`，
`gh pr view 63 --json statusCheckRollup` → `[]`。

**后果**：PR #63 携带的 v13 DoD #4（Replay Integrity Guard，51 个新测试）+ DoD #6（`docs/REPRODUCE.md` v1.0，723 行）**从未被 CI 验证过**。

这个缺口之所以特别危险，是因为它**看起来不像故障**：

- 失败的 CI 是**红的** —— 没人会忽略。
- 还在跑的 CI 是**灰的** —— 有人会等。
- **零检查**在 PR 页面上只是一片空白 —— 它看起来像"还没开始"，而不是"永远不会开始"。

于是 v123 早场 / 晚场的 run log 里都写着"PR #63 OPEN + CLEAN + MERGEABLE"，
把 MERGEABLE 当成了"已验证"。**MERGEABLE 说的是能合并，不是已验证。**
`statusCheckRollup: []` 才是真相，而它一直就在那里，只是没人去问。

> 附带修正：v123 两轮 run log 记为"CI 6/6 SUCCESS"的状态**对 PR #63 不成立**（实际是 0 次运行）。
> 本轮已把这一事实性错误在 ADR / NEXT_ROUND_THEME / run log 中更正。

### 解法

**1. 触发块：去掉 `pull_request` 上的 `branches:` 过滤器。**

```yaml
on:
  push:
    branches: [master, daily/*, fix/*, feature/*]
  pull_request:      # ← 不再有 branches 过滤器
```

无过滤 = 任何 base 分支的 PR 都会启动 CI。`push` 过滤器保持不变（`feat/*` 不在其中），
所以推 feature 分支**不会**触发重复的 push 构建 —— 只有 PR 事件会跑，一份构建。

**2. 新增 `scripts/ci_trigger_audit.py`：把不变量变成可执行的门禁。**

一个无依赖的小工具，读取 workflow 的 `on:` 触发块，回答 GitHub 会回答的那个问题：
**"一个 base 为 X 的 PR，会触发 CI 吗？"**

- **零第三方依赖**：PyYAML 在开发容器里有，但**不在 `requirements.lock`**，
  import 它会直接搞挂 CI。所以这里写了一个只覆盖 Actions 触发块这一种形状的
  子集解析器（嵌套一级 / flow list `[a, b]` / block list `- a`）。
  遇到看不懂的形状**抛异常而不是猜** —— 一个静默返回"无过滤器"的解析器会让审计**说谎**。
- **只读**：审计从不改写 workflow。修不修 workflow 是人的决定，工具的职责是让缺口**可见**且**可测**。
- **可直接当 CI 门禁用**：`exit 0` = 无缺口，`exit 1` = 有缺口。

**3. CI 里新增 `ci-trigger-audit` job：自举守卫。**

这个 job 自己跑在 CI 里，检查 CI 的触发块有没有被再次收窄。
一旦有人再写回 `branches: [master]`，**构建会自己失败**。

```yaml
ci-trigger-audit:
  runs-on: ubuntu-latest
  steps:
    - uses: actions/checkout@v4
    - uses: actions/setup-python@v5
      with: { python-version: '3.12' }
    - name: Audit CI trigger coverage
      run: python3 scripts/ci_trigger_audit.py
```

> 注意这个 job **不需要** `pip install -r requirements.lock` —— 审计脚本只用标准库。
> 这很关键：如果守卫自己依赖 CI 环境里可能出问题的包，它就会和它要守护的东西一起失效。

**4. `tests/test_ci_trigger_audit.py`：19 个测试钉住不变量。**

两类测试：

- **解析器行为**：flow list / block list / 无过滤器 / 注释不被误认成事件 / 行尾注释 / 缺 `on:` 抛异常 / GitHub 通配符语义（`*` 不跨 `/`，`**` 跨 `/`，`?` 单字符）。
- **仓库自身的不变量**：`ci.yml` 的 `pull_request` 过滤器必须是 `None`（**最重要的一条**）；每个 base 分支都被覆盖；脚本 exit 0。

### 设计约束

- **守卫必须零依赖**：否则守卫会和它守护的东西一起挂掉。
- **审计只读**：不改 workflow、不改历史、不隐藏缺口。
- **不过度触发**：去掉 `pull_request` 过滤器**不会**造成 push + PR 双跑，因为 `push` 的过滤器不含 `feat/*`。
- **不掩盖失败**：审计发现缺口时 `exit 1`，让构建红掉 —— 宁可红，不要静默。

### 修复后的覆盖

```
🔍 CI trigger coverage audit
============================================================
📄 .github/workflows/ci.yml
   events: push, pull_request
   pull_request base filter: (no filter — every base branch)
     ✅ base=master
     ✅ base=main
     ✅ base=feat/v12-sdk-foundation
     ✅ base=feat/v13-provenance-provenance
     ✅ base=feat/v13-replay-provenance
     ✅ base=feat/v13-replay-integrity-guard

📄 .github/workflows/release.yml
   events: push
   pull_request base filter: n/a — workflow does not run on pull requests

✅ Every pull request base branch is covered by CI.
```

> `release.yml` 是 tag 驱动的发布工作流，**本来就不该**在 PR 上跑。
> 审计脚本因此不会把它算成缺口 —— 只有订阅了 `pull_request` 的 workflow 才可能留下缺口。

### 本轮最重要的产出不是"加了 19 个测试"

而是**把一个一直存在、但从未被测量的假设变成了 CI 会主动拦住的门禁**。

在这次修复之前，"CI 覆盖了所有 PR" 是一句**没人验证过的话**。
它恰好在唯一一次不成立的时候（PR #63），静悄悄地失效了两轮。
现在它是一条**CI 每次都检查、违反就红**的规则。
