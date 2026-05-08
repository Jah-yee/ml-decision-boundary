# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**版本：** v6（PR#23 fix/ci-smoke-flag 创建，v3 DoD 第2项评估启动）
**更新时间：** 2026-05-08 21:46 CST
**维护人：** 太子

---

## 📋 当前阶段状态

### v1 DoD（已完成 ✅）
- [x] pytest 覆盖率 ≥ 80%（当前 89%）
- [x] API 端点全测试覆盖（19个测例）
- [x] benchmark 命令标准化
- [x] 安全修复（traceback.format_exc() 移除）
- [x] REPRODUCE.md 新建

### v2 DoD（已完成 ✅）
- [x] pip-compile / pip-lock 流程 ✅ (2026-05-02)
- [x] Tree depth 敏感性测试矩阵 ✅ (2026-05-01 evening)
- [x] v1 → v2 阶段升级 ADR ✅ (ADR-0002, PR#18)
- [x] SPEC.md 拆分 ✅ (PR#19, 2026-05-03)
- [x] CLI 帮助文本改进 ✅ (2026-05-05: main.py argparse + benchmarks/run.py --help epilog)
- [x] GitHub Actions CI 配置 ✅ (PR#21, 2026-05-06)
- [x] CONTRIBUTING.md 完善 ✅ (PR#21, 2026-05-06)

### v3 DoD（进行中）
- [x] benchmark 报告 HTML 化 ✅ (PR#22: report_html.py + trend charts + daily reports)
- [x] ADR-0003 phase v2→v3 升级判定 ✅ (2026-05-08)
- [ ] 新模型支持或超参数调优实验体系
- [ ] 新数据集支持
- [ ] CLI/Web/API 平台化

---

## 🔍 深度扫描发现（2026-05-08 evening）

### 高优先级
| 发现 | 来源 | 估计时间 | 修复 |
|------|------|---------|------|
| CI P2 step `--smoke` flag 不存在 | 深度扫描 | 5分钟 | PR#23 fix/ci-smoke-flag ✅ |

### 中优先级
| 发现 | 来源 | 估计时间 |
|------|------|---------|
| report_html.py API 文档缺失（`generate_report` vs `generate_html_report`） | 深度扫描 | 10分钟 |

---

## 🎯 下一轮深度维护方向

### 主攻：CI 验证 + v3 DoD 第2项（新数据集支持）
**来源：** evening 场发现 PR#23 待 merge + v3 DoD 候选
**问题：** PR#23 fix/ci-smoke-flag 已创建，需验证 CI 是否通过；新数据集支持是 v3 DoD 高优先级待办
**工作内容：**
1. 检查 PR#23 CI 状态，如通过则 merge
2. 评估 make_classification 可扩展性
3. 添加新数据集 fixture（可选：anomaly/sparse/clustered）
4. 更新 benchmark 矩阵

**估计时间：** 45分钟

### 次攻：新模型支持
**来源：** v2 附加目标
**问题：** 当前模型族可扩展 GradientBoosting / XGBoost
**工作内容：**
1. 评估新模型与现有 benchmark harness 兼容性
2. 添加新模型到 benchmarks/run.py MODELS 字典
3. 更新阈值配置

**估计时间：** 60分钟

### 次攻：report_html.py API 文档修复
**来源：** 深度扫描中优先级发现
**问题：** `generate_html_report()` 函数名不存在，实际为 `generate_report(reports_dir, output_dir)`
**工作内容：** 更新 CONTRIBUTING.md 中 benchmark 命令说明，或添加 `generate_html_report` 作为 alias

**估计时间：** 10分钟

---

## 📊 深度维护指标（v3 追踪起点）

| 指标 | 说明 | 目标 |
|------|------|---------|
| commit_per_session | 每会话 commit 数 | ≥2 |
| problem_solved | 真正解决问题的比例 | ≥80% |
| doc_quality | 文档无硬造 | ≥90% |
| p0_pass | P0 compileall | 100% |
| p1_pass | P1 pytest | 100% |
| p2_pass | P2 benchmark | ≥90% |

---

## 🎯 本轮执行总结（2026-05-08 evening）

**本轮完成：**
- ✅ 深度扫描发现 CI P2 step 失败根因（`--smoke` vs `--quick` flag）
- ✅ 创建 PR#23 fix/ci-smoke-flag（1行修复）
- ✅ 刷新 2026-05-08 benchmark 报告（full-suite: 52 exp, 45/7 pass/fail, avg 0.8237）
- ✅ 添加 depth sweep 2026-05-08（24 exp, 22 passed）
- ✅ 更新 strategy/runs/2026-05-08-2146.md

**本轮 commit 历史（4个）：**
1. `82c7bc5` docs(benchmarks): refresh 2026-05-08 reports with latest full-suite run
2. `d3d720d` docs(benchmarks): add depth sweep 2026-05-08 (24 experiments, 22 passed)
3. `0a09b77` docs(strategy): evening session run log 2026-05-08
4. `f4cda64` fix(ci): use --quick instead of --smoke for benchmark smoke test（fix/ci-smoke-flag 分支，PR#23）

**时间分配：**
```
扫描 + 分析：20分钟
CI 问题定位：10分钟
修复（fix/ci-smoke-flag）：10分钟
报告刷新（full-suite + depth sweep）：25分钟
Push + PR + 收尾：15分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **CI 问题分析** — GitHub Actions UI 报告的 failure step 未必是根因（底层 step 被标记为 failure 而非真正失败的 step）
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution
5. **v3 DoD 首项 + ADR-0003 已完成** — 下一轮可启动 CI 验证 + v3 DoD 第2项（新数据集/新模型）

---

**下次更新：** 下一轮 cron 执行后（2026-05-09）
