# CHARTER — ml-decision-boundary

**版本**: v0.2 (Updated 2026-04-26: commit → PR → review → merge 闭环，每日两次)  
**北极星方向**: 从早期可视化/实验工具演化为「可扩展 ML 实验与可视化平台」

---

## Vision

成为 ML 工程师、教育者和学生的首选工具：看一眼决策边界，就能理解模型几何、调试非线性分类器、建立参数直觉。长期目标是成为"ML 决策边界的 Observable"，让每次实验都像写 Jupyter notebook 一样简单，但产出可复现、可比较、可部署的结果。

---

## Mission

日常交付三类价值：

1. **科学价值**: 通过 2D 可视化揭示模型几何本质，帮助建立对 SVM/Tree/KNN/MLP 的直觉；记录负结果（失败模式同样重要）。
2. **产品价值**: 交付即开即用的 CLI/Web/API 产品；做到零配置 demo，一行命令复现论文级别的可视化。
3. **工程价值**: 建立 Harness 可复现实验体系，让每一次训练都可追溯、可回归测试、可集成到部署流水线。

---

## Non-Goals（明确不做什么）

- 不做 AutoML / 超参数搜索平台（但提供参数 sweep 可视化）
- 不做通用数据处理 pipeline（专注 2D 合成数据，扩展前必须通过 charter 评审）
- 不做模型生产部署托管（API 只做预测接口，不是模型注册表）
- 不做多语言 SDK（Python first，偶尔 Web JS demo）

---

## Quality Bar（P0-P3 通过层级）

| 层级 | 定义 | 验证命令 |
|------|------|----------|
| **P0** | `python3 -m compileall .` 无错误；`python3 -c "import main; print('OK')"` 成功 | 见上方 |
| **P1** | pytest -q 通过（或本轮至少建立测试基础设施 + 1 个测例） | `pytest -q` |
| **P2** | 运行 benchmarks/ 下的缩小版 harness，输出报告到 benchmarks/reports/YYYY-MM-DD.md | `python3 main.py` |
| **P3** | API/Web 行为在 spec 中记录；health endpoint 返回 200 | curl localhost:5000/api/health |

---

## 当前阶段

见 `phases.md`

---

## Quality Bar（P0-P3 通过层级）

| 层级 | 定义 | 验证命令 |
|------|------|----------|
| **P0** | `python3 -m compileall .` 无错误；`python3 -c "import main; print('OK')"` 成功 | 见上方 |
| **P1** | pytest -q 通过（或本轮至少建立测试基础设施 + 1 个测例） | `pytest -q` |
| **P2** | 运行 benchmarks/ 下的缩小版 harness，输出报告到 benchmarks/reports/YYYY-MM-DD.md | `python3 main.py` |
| **P3** | API/Web 行为在 spec 中记录；health endpoint 返回 200 | curl localhost:5000/api/health |

---

## 维护约定

- Charter 每轮 review 时检查是否需要更新
- 重大架构决策写入 `docs/adr/`（用 ADR 编号）
- 所有 commit author: `Jah-yee <jydu_seven@outlook.com>`

---

## PR/Commit 闭环工作流（v0.2）

### 频率
- 每天运行 **两次**：上午场 + 下午场
- 每次完成一个完整的小闭环：思考 → 开发 → 本地Review → commit → PR → 等merge

### 每次闭环步骤

| # | 阶段 | 说明 |
|---|------|------|
| 1 | **Manage（规划）** | 读取 playbook + NEXT_ROUND_THEME，明确本轮主题和目标通过层级 |
| 2 | **Develop（开发）** | 按 playbook 执行 7 步闭环（a-g），产出真实代码/文档改动 |
| 3 | **Golden Rule（自审）** | 本地运行 `python3 -m compileall .` + `pytest -q`，确认 P0/P1 通过后再继续 |
| 4 | **Review（评审）** | 读取改动的 diff，检查：必要文件、diff范围、commit message、author、无新问题 |
| 5 | **Commit** | 用 Jah-yee 身份提交到本地分支 |
| 6 | **PR 创建** | push 后在 GitHub 上创建 PR，标题=commit message，说明本轮改动摘要 |
| 7 | **等 Merge** | PR 审核通过后由人工/自动合并（或配置 branch protection 自动 merge on approval） |

### PR 描述模板

```markdown
## 本轮主题
{一句话描述本轮唯一主题}

## 改动摘要
- P0/P1/P2/P3 通过层级状态
- 触及文件列表
- 资源使用（运行时间/内存）

## 下轮待办
1. ...
```

### Golden Rule（必须自查）

> 每次 commit 前必须满足：
> - ✅ `python3 -m compileall .` 无错误
> - ✅ `pytest -q` 通过（P1）
> - ✅ diff 最小（只改必要文件）
> - ✅ author 为 Jah-yee <jydu_seven@outlook.com>
> - ✅ commit message 清晰描述改动

### Review 检查清单

- [ ] P0 通过（compileall + import smoke）
- [ ] P1 通过（pytest 通过）
- [ ] diff 只改必要文件
- [ ] commit message 清晰
- [ ] author 正确
- [ ] 无新问题引入
- [ ] PR 描述完整
- [ ] 最优（没有更小/更简洁的实现方式了吗？）
