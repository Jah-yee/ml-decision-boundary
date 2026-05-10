# ADR-0003 — Phase v2 → v3 升级判定

**日期**: 2026-05-08
**状态**: Accepted
**决策者**: ml-decision-boundary cron agent (taizi)

---

## 背景

v2 Model & Data Expansion 阶段的 DoD 条目已全部完成。本 ADR 记录正式的阶段升级判定，并为 v3 阶段建立基线。

v2 阶段完成了 CLI 帮助文本改进、SPEC.md 拆分、GitHub Actions CI 配置、CONTRIBUTING.md 完善等关键交付物，同时 benchmark 报告 HTML 化作为 v3 入口成果已落地（PR#22）。

---

## v2 阶段 DoD 实际完成情况

| DoD 条目 | 状态 | 证据 |
|---------|------|------|
| SPEC.md 拆分 | ✅ 完成 | PR#19 (2026-05-03)，spec/ 目录重构 |
| CLI 帮助文本改进 | ✅ 完成 | PR#20 (2026-05-05)，main.py argparse + benchmarks/run.py --help epilog |
| GitHub Actions CI 配置 | ✅ 完成 | PR#21 (2026-05-06)，P0 compileall + P1 pytest + P2 benchmark smoke |
| CONTRIBUTING.md 完善 | ✅ 完成 | PR#21 (2026-05-06)，含快速开始、P0/P1/P2 gates、branch/PR workflow |
| ADR-0002: Phase v1 → v2 升级 | ✅ 完成 | commit 981f802 (2026-05-02) |

### v2 附加交付物（超出 DoD）

| 交付物 | 描述 |
|--------|------|
| benchmark 报告 HTML 化 | benchmarks/report_html.py (372行)，3种趋势图（accuracy/train_time/summary） |
| Daily report 自动化 | benchmarks/run.py --html flag，每日自动生成 HTML + PNG charts |
| pip-compile / pip-lock 流程 | DEPENDENCY_POLICY.md + requirements.lock |
| Tree depth sensitivity sweep | `--depth-sweep` flag，24实验矩阵 |
| research/2026-05-01-tree-depth-sensitivity.md | Tree depth 失败模式研究文档 |

---

## v3 阶段定义：Platform

**目标**: 完整的 CLI/Web/API 平台化

### v3 入口条件（从 v2 继承）
- P0 ✅ (python3 -m compileall . 无错误)
- P1 ✅ (pytest 67 快速测例全通过，核心路径覆盖)
- P2 ✅ (benchmarks/reports 可重复产出，Accuracy 0.79 >= 0.70)
- GitHub Actions CI ✅ (P0/P1/P2 三层门禁)
- benchmark HTML 报告 ✅ (benchmarks/report_html.py，PR#22)

### v3 阶段 DoD（待填充）

```
- [ ] 新模型支持或超参数调优实验体系
- [ ] 新数据集支持
- [ ] CLI/Web/API 平台化
- [ ] ADR-0003 本 ADR 创建 ← 本轮交付
```

---

## v3 阶段 DoD 候选（待本轮决策）

### DoD Item 1: 新模型支持（GradientBoosting / XGBoost）
**问题**: 当前模型族仅有 SVM / RandomForest / DecisionTree，可扩展 GradientBoosting / XGBoost
**工作内容**:
1. 评估新模型与现有 benchmark harness 兼容性
2. 添加新模型到 benchmarks/run.py MODELS 字典
3. 更新阈值配置

**估计时间**: 60分钟

### DoD Item 2: 新数据集支持
**问题**: 当前只有 circles / moons / blobs / xor，可扩展 make_classification 参数矩阵
**工作内容**:
1. 评估新增数据集的可行性
2. 添加新的数据集 fixture
3. 更新 benchmark 矩阵

**估计时间**: 45分钟

### DoD Item 3: CLI/Web/API 平台化
**问题**: 当前 CLI/Web/API 尚未平台化，缺少统一入口
**工作内容**:
1. 统一 CLI 入口（argparse subcommand）
2. Web Flask API 平台化
3. API 文档（OpenAPI/Swagger）

**估计时间**: 90分钟

---

## 升级判定

**v2 → v3 阶段升级条件已满足。**

判定依据：
- v2 DoD 全部 5 项 ✅
- v2 附加交付物（benchmark HTML 化、CI 配置）✅
- phases.md 当前阶段标注 "v2 进行中"，需更新为 "v3 进行中"

---

## 决策

v2 阶段正式结束，当前阶段更新为 v3 — Platform。
phases.md 将同步更新。

---

## 下一步

1. 更新 `spec/phases.md`：将"当前阶段: v2 — Model & Data Expansion"改为"当前阶段: v3 — Platform"
2. 清理 phases.md 中 v2 的已完成 DoD 标记
3. 向 CHANGELOG.md Unreleased 添加 v2→v3 升级条目
4. 下一轮 cron 可继续 v3 DoD：选 DoD Item 1（新模型支持）或 Item 2（新数据集支持）

---

## 参考

- ADR-0002: Phase v1 → v2 升级判定（2026-05-02）
- ADR-0001: Phase v0 → v1 升级判定（2026-04-27）
- benchmarks/report_html.py — HTML 报告生成器（PR#22）
- benchmarks/reports/2026-05-08.{html,json.md} — 今日 benchmark 报告
