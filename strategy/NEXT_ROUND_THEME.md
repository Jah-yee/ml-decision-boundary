# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**更新时间：** 2026-05-06 09:52 CST
**版本：** v3（v2 DoD 全部完成）
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
- [x] SPEC.md 拆分 ✅ (2026-05-03, PR#19)
- [x] CLI 帮助文本改进 ✅ (2026-05-05: main.py argparse + benchmarks/run.py --help epilog)
- [x] GitHub Actions CI 配置 ✅ (2026-05-06)
- [x] CONTRIBUTING.md 完善 ✅ (2026-05-06)

### v3 DoD（下一阶段）
- [ ] benchmark 报告 HTML 化（可视化趋势图）
- [ ] 新模型支持或超参数调优实验体系
- [ ] 新数据集支持
- [ ] CLI/Web/API 平台化

---

## 🎯 下一轮深度维护方向

### 主攻：benchmark 报告 HTML 化
**来源：** v2 附加目标 / 分叉 #1 高优先级
**问题：** 当前 benchmark 报告只有 JSON + Markdown，缺少可视化趋势
**工作内容：**
1. 研究 benchmark 报告 HTML 化方案（plotly / matplotlib）
2. 生成历史数据趋势图（准确率 / 训练时间）
3. 更新 benchmark run 脚本支持 HTML 输出

**估计时间：** 60分钟

### 次攻：新数据集支持评估
**来源：** v2 附加目标
**问题：** 当前只有 circles / moons / blobs / xor，可扩展更多合成场景
**工作内容：**
1. 评估新增数据集的可行性（make_classification 参数）
2. 添加新的数据集 fixture
3. 更新 benchmark 矩阵

**估计时间：** 45分钟

---

## 🔍 深度扫描待办池

### 高优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| benchmark 报告 HTML 化 | v2 附加目标 | 60分钟 | #1 |
| 新数据集支持 | v2 附加目标 | 45分钟 | #2 |

### 中优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| 新模型支持 | v2 附加目标 | 60分钟 | #2 |
| 超参数调优实验 | v2 附加目标 | 45分钟 | #2 |
| ADR-0003: v2 → v3 升级判定 | 阶段演进 | 30分钟 | #5 |

### 低优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| CODEOWNERS 配置 | 社区工程 | 20分钟 | #5 |
| pip-audit 集成 | 依赖安全 | 20分钟 | #5 |

---

## 📊 深度维护指标（v3 追踪起点）

> 从 v3 开始追踪

| 指标 | 说明 | 目标 |
|------|------|---------|
| commit_per_session | 每会话 commit 数 | ≥2 |
| problem_solved | 真正解决问题的比例 | ≥80% |
| doc_quality | 文档无硬造 | ≥90% |
| p0_pass | P0 compileall | 100% |
| p1_pass | P1 pytest | 100% |
| p2_pass | P2 benchmark | ≥90% |

---

## 🎯 本轮执行建议

### 会话类型：专项深挖（benchmark HTML 化）

**本轮已完成：**
- ✅ GitHub Actions CI 配置（.github/workflows/ci.yml）
- ✅ CONTRIBUTING.md 完善
- ✅ benchmark 报告归档（2026-05-05 + 2026-05-06）
- ✅ v2 DoD 全部完成（6/6 项）

**下一轮建议（专项深挖）：**
- 主攻：benchmark 报告 HTML 化
- 次攻：新数据集评估

**时间分配（90分钟）：**
```
扫描 + 规划：10分钟
benchmark HTML 化：50分钟
验证 + 收尾：20分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **多个相关 commit** — 不要为了"快速闭环"只做一个 PR
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution
5. **v2 DoD 全部完成** — 下一轮可启动 v2→v3 ADR 或直接进入 v3 附加目标

---

**下次更新：** 下一轮 cron 执行后（2026-05-06 evening 或 2026-05-07）
