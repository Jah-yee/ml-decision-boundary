# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**更新时间：** 2026-05-08 10:11 CST
**版本：** v4（v3 DoD 首项已完成 ✅）
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
- [x] benchmark 报告 HTML 化 ✅ (PR#22, 2026-05-08: report_html.py + trend charts + daily reports)
- [ ] 新模型支持或超参数调优实验体系
- [ ] 新数据集支持
- [ ] CLI/Web/API 平台化

---

## 🎯 下一轮深度维护方向

### 主攻：v2→v3 阶段升级 ADR
**来源：** 阶段演进
**问题：** benchmark HTML 化已完成，触发 v3 入口条件
**工作内容：**
1. 评审 benchmark HTML 化作为 v3 入口成果
2. 新建 `docs/adr/ADR-0003-phase-v2-to-v3.md`
3. 更新 `spec/phases.md` v3 状态

**估计时间：** 30分钟

### 次攻：新数据集支持评估
**来源：** v2 附加目标
**问题：** 当前只有 circles / moons / blobs / xor，可扩展更多合成场景
**工作内容：**
1. 评估新增数据集的可行性（make_classification 参数）
2. 添加新的数据集 fixture
3. 更新 benchmark 矩阵

**估计时间：** 45分钟

### 次攻：新模型支持
**来源：** v2 附加目标
**问题：** 当前模型族可扩展 GradientBoosting / XGBoost
**工作内容：**
1. 评估新模型与现有 benchmark harness 兼容性
2. 添加新模型到 benchmarks/run.py MODELS 字典
3. 更新阈值配置

**估计时间：** 60分钟

---

## 🔍 深度扫描待办池

### 高优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| v2→v3 阶段升级 ADR | 阶段演进 | 30分钟 | #5 |
| 新数据集支持 | v2 附加目标 | 45分钟 | #2 |

### 中优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| 新模型支持 | v2 附加目标 | 60分钟 | #2 |
| 超参数调优实验 | v2 附加目标 | 45分钟 | #2 |
| CODEOWNERS 配置 | 社区工程 | 20分钟 | #5 |

### 低优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| pip-audit 集成 | 依赖安全 | 20分钟 | #5 |

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

## 🎯 本轮执行总结（2026-05-08 晨间场）

**本轮完成：**
- ✅ benchmark 报告 HTML 化（PR#22: report_html.py + 3 chart types + daily reports）
- ✅ push 到 GitHub + PR 创建（PR#22）
- ✅ 修复 GH007 private email 问题（noreply email）
- ✅ 归档昨日 evening run log（strategy/runs/2026-05-07-2152.md）

**本轮 commit 历史（3个）：**
1. `docs(benchmarks): daily report 2026-05-08 + archive prior run log`
2. `docs(benchmarks): add 2026-05-07 HTML reports (from evening session)`
3. `docs(benchmarks): add 2026-05-08 trend chart PNGs`

**时间分配：**
```
扫描 + 规划：10分钟
P0/P1 验证：15分钟
报告生成 + push：20分钟
PR 创建 + 收尾：15分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **多个相关 commit** — 本轮做了3个 commit，避免为"快速闭环"只做一个
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution
5. **v3 DoD 首项已完成** — 下一轮可启动 v2→v3 ADR 或继续 v3 附加目标

---

**下次更新：** 下一轮 cron 执行后（2026-05-08 evening 或 2026-05-09）
