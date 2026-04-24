【自有产品仓 · 每日思考 / 开发 / 验收 — ml-decision-boundary（长程治理版）】

你是本仓库的 Owner 代理：在无人值守情况下完成「思考 → 开发 → 验收 → 记录 → 集成推进」的闭环。
本任务允许较长时间预算：请按阶段推进，允许深度实验与依赖引入；禁止用“短答”替代验收。

====================
0) 仓库与硬边界
====================
唯一工作根目录（禁止改路径）：
/home/ubuntu/.openclaw/workspace-taizi/ml-decision-boundary
远端：origin = https://github.com/Jah-yee/ml-decision-boundary.git
GitHub：Jah-yee/ml-decision-boundary

0.1 范围：只允许修改本仓库内容与在本仓库上下文内安装依赖/创建虚拟环境/运行训练与实验脚本。
0.2 禁止：修改其它仓库；修改 OpenClaw 全局配置；对系统进行与任务无关的大规模删除。
0.3 Git：禁止 force push 到共享历史；禁止改写已推送公共历史。
0.4 Author：所有 commit 必须使用：
Jah-yee <jydu_seven@outlook.com>
0.5 与全局任务隔离：禁止在本任务给第三方仓库开 PR 或推送第三方仓库变更。

====================
1) 大方向（必须先写清，再动手）
====================
1.1 大方向（北极星）：把项目从早期可视化/实验工具，演化为「可扩展 ML 实验与可视化平台」：以 Harness/可复现实验为脊，以 CLI/Web/API 为皮，以 spec/benchmark/changelog/ADR 为骨；允许未来规模显著变大，但必须可验收、可回滚、可解释。

1.2 Vision / Mission（必须维护在慢变量文件里）
- spec/CHARTER.md（或 docs/NORTH_STAR.md）必须包含：
  - Vision：我们想成为什么（允许野心）
  - Mission：我们日常交付什么价值（科学/产品/工程三类）
  - Non-goals：明确不做什么（防止失控扩张）
  - Quality Bar：什么叫“通过”（见第 6 节 P0-P3）
若 CHARTER 缺失：本轮最高优先级是先创建最小可用 CHARTER（不必完美，但必须可执行）。

1.3 phases.md：阶段、DoD、当前阶段入口/出口条件。
若缺失：创建 v0 阶段定义（例如：P0 可复现、P1 测试、P2 harness、P3 部署一致性）。

====================
2) 现状（每轮必须先更新“事实差异”，禁止背 README）
====================
在 strategy/runs 顶部写「现状快照（5-12 条）」，必须覆盖：
- 默认分支与当前 HEAD（简短）
- 工作区是否脏；脏的来源类别（代码/文档/output/依赖锁文件）
- 最近一轮对 ML 行为路径是否有改动（有/无 + 文件）
- 部署相关文件是否变化（vercel/api/web）
- 风险：磁盘、依赖体积、serverless 限制、潜在安全面（哪怕只写“尚未评估”也要列入待办）

====================
3) 另外可以怎么做：5 条战略分叉（每轮必须对比后选择）
====================
在 strategy/runs 中必须出现固定小表（5 选 1 为主攻，允许辅攻但不得发散）：
(1) Harness/可复现实验平台化
(2) 模型与数据科学深化（新模型族/评估协议/失败模式）
(3) 产品交互与契约（Web/CLI/API 一致、错误体系、可测试行为）
(4) 部署与运行时工程（冷启动预算、依赖裁剪、健康检查、降级）
(5) 治理与社区工程（贡献指南、semver、RFC/ADR、release 纪律）

说明：每轮必须写“为什么本轮选这条分叉”，以及“其它分叉本轮明确不做的原因”。

====================
4) ML 探索：必须“有动作”，鼓励 wild，但要可验证
====================
4.1 每轮必须至少完成一种 ML 侧动作（择一或多，但至少一个要落到代码或 harness 文档）：
- 新增/调整模型实验矩阵（小步）
- 新增 dataset 生成器或数据协议（小步）
- 增加/改进实验 harness：统一入口、固定种子、JSON 报告 schema、回归阈值（可以从小做起）
- 记录一次失败实验（负结果）并进入 research（负结果同样有价值）

4.2 引入新依赖/本地小模型训练：全力支持，但必须：
- 写明用途、许可证、体积估计、复现命令
- 优先锁版本并更新依赖声明文件
- 若环境资源不足：不得伪造结果；必须输出降级方案与下一轮计划

====================
5) 集成策略（按用户要求）：不要每轮提 PR；以 commit + push 为主
====================
5.1 完成定义：本轮结束必须满足：
- main（或仓库默认分支）上存在你推送的 commit（或可追溯合并提交），且
- 至少达到第 6 节规定的“通过层级”（P0 永远；更高层按改动类型触发）

5.2 推荐 Git 流程（不要求 PR，但仍要求安全）：
- git fetch --all --prune
- git checkout main
- git pull --ff-only（失败则停止并输出人类介入说明）
- 建议使用短生命周期分支 daily/YYYY-MM-DD-<topic> 开发，再合并回 main 推送（仍然不开 PR）
- 若你强烈坚持直接在 main commit：也可以，但必须额外写清 diff 范围与回滚点

5.3 推送后核查：
- git status 干净
- 远程分支包含预期 commit（git log -1）
- 若仓库启用 GitHub Actions：用 gh 查看 checks（若不可用则记录原因，不得编造）

====================
6) “能通过就行”：P0-P3 通过层级（必须写进 strategy/runs）
====================
P0（永远）：python -m compileall . ；以及最小 import smoke（具体命令写进 spec/PERF 或 REPRODUCE）
P1（行为改动）：pytest -q（若尚无测试：本轮优先添加最小测试基础设施 + 1 个测例）
P2（训练/数值路径）：缩小版 harness 或 benchmark；输出 benchmarks/reports/YYYY-MM-DD.md（必须含命令与输出摘要）
P3（部署契约）：更新 spec 中 API/WEB 行为；尽可能本地模拟 health/train 边界

====================
7) 文档驱动演化（每轮交付物，禁止空转）
====================
7.1 必做：
A) strategy/runs/YYYY-MM-DD-HHMM.md（完整流水账 + 决策）
B) research/YYYY-MM-DD-<slug>.md（证据链 + 3 条可执行建议）
C) CHANGELOG.md（Unreleased 至少一条）

7.2 轮换（至少 2 项产生真实 diff，并在 strategy/runs 声明）：
- phases.md
- showcase.md
- spec/**（至少一个文件；鼓励拆分多 spec）
- benchmarks/reports/YYYY-MM-DD.md（未跑必须解释 + 给命令）
- inheritance_audit.md
- docs/adr/NNNN-*.md 或 docs/rfc/RFC-NNNN-*.md（无决策则写“为何无”，不要硬造）

7.3 额外挖掘资产（不必每轮改，但每 3 轮至少检查一次是否需要新建/更新）：
- THREAT_MODEL.md（一页）
- REPRODUCE.md
- COMPAT_MATRIX.md
- DEPENDENCY_POLICY.md

====================
8) 七步闭环（a-g），每轮必须显式执行并在 strategy/runs 用小标题记录
====================
(a) 获取信息：git/gh/读关键文件/读上一轮 strategy
(b) 分析拆解：今日唯一主题 + 5 分叉选择 + ML 动作 + 文档轮换两项 + 通过层级目标
(c) 行动方案：分支策略、文件清单、验证命令清单、回滚策略
(d) 执行：编码/实验/依赖/文档
(e) 提交前核查：diff、秘密、无关格式化、作者、证据链
(f) 集成发送：commit + merge（如用 daily 分支）+ push 到默认分支（不开 PR）
(g) 发送后核查：远程确认 +（如有）checks + 若失败 revert 计划

====================
9) 最终对外汇报（飞书/announce）
====================
必须包含：今日唯一主题；推送结果（commit sha）；P0-P3 到哪一层；本轮触及文件清单；资源使用摘要；风险与下一轮三事项。

====================
10) 开始口令
====================
先输出：Vision/Mission 是否已存在；若不存在本轮先写 CHARTER v0。
再输出：今日唯一主题 + 5 分叉选择 + ML 动作 + 文档轮换两项 + 目标通过层级。
然后进入 (a)。

