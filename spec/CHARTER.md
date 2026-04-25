# CHARTER — ml-decision-boundary

**版本**: v0.1 (Created 2026-04-26, owner cron闭环)  
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

## 维护约定

- Charter 每轮 review 时检查是否需要更新
- 重大架构决策写入 `docs/adr/`（用 ADR 编号）
- 所有 commit author: `Jah-yee <jydu_seven@outlook.com>`
