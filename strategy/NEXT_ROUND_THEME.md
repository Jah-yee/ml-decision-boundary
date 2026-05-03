# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**更新时间：** 2026-05-02 09:55 CST
**版本：** v2（深度维护版）
**维护人：** 太子

---

## 📋 当前阶段状态

### v1 DoD（已完成 ✅）
- [x] pytest 覆盖率 ≥ 80%（当前 89%）
- [x] API 端点全测试覆盖（19个测例）
- [x] benchmark 命令标准化
- [x] 安全修复（traceback.format_exc() 移除）
- [x] REPRODUCE.md 新建

### v2 DoD（进行中）
- [x] pip-compile / pip-lock 流程 ✅ (2026-05-02)
- [x] Tree depth 敏感性测试矩阵 ✅ (2026-05-01 evening)
- [x] v1 → v2 阶段升级 ADR ✅ (ADR-0002, PR#18)
- [ ] SPEC.md 拆分
- [ ] CLI 帮助文本改进

---

## 🎯 下一轮深度维护方向

### 主攻：SPEC.md 拆分
**来源：** v2 DoD
**问题：** docs/ 目录（原 spec/）混杂
**工作内容：**
1. 将 docs/ 目录中的文档分类（spec/ 保留核心规范，其他移入 docs/）
2. 创建 SPEC.md 作为核心规范入口
3. 更新相关引用

**估计时间：** 45分钟

### 次攻：CLI 帮助文本改进
**来源：** v2 DoD
**问题：** main.py 和 benchmarks/run.py 的 CLI 帮助文本和错误提示可优化
**工作内容：**
1. 审查现有 CLI 帮助文本
2. 改进 `--help` 输出和错误提示
3. 确保子命令都有清晰 docstring

**估计时间：** 30分钟

---

## 🔍 深度扫描待办池

### 高优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| SPEC.md 拆分 | v2 DoD | 45分钟 | #5 |
| CLI 帮助文本改进 | v2 DoD | 30分钟 | #3 |

### 中优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| SPEC.md 拆分 | docs/混杂 | 45分钟 | #5 |
| CLI 帮助文本改进 | 产品体验 | 30分钟 | #3 |
| CONTRIBUTING.md 完善 | 社区工程 | 30分钟 | #5 |

### 低优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| CONTRIBUTING.md 完善 | 社区工程 | 30分钟 | #5 |
| GitHub Actions 缓存优化 | CI/CD | 20分钟 | #5 |
| benchmark 报告 HTML 化 | Harness | 60分钟 | #1 |

---

## 📊 深度维护指标

> 从 v3 playbook 开始追踪

| 指标 | 说明 | 目标 |
|------|------|------|
| commit_per_session | 每会话 commit 数 | ≥2 |
| problem_solved | 真正解决问题的比例 | ≥80% |
| doc_quality | 文档无硬造 | ≥90% |
| p0_pass | P0 compileall | 100% |
| p1_pass | P1 pytest | 100% |
| p2_pass | P2 benchmark | ≥90% |

---

## 🎯 本轮执行建议

### 会话类型：快速闭环

**本轮已完成：**
- ✅ v1→v2 阶段升级 ADR（PR#18, commit 8df3911）
- ✅ phases.md 更新（v1完成，v2当前阶段）
- ✅ CHANGELOG.md 更新

**下一轮建议（专项深挖）：**
- 主攻：SPEC.md 拆分
- 次攻：CLI 帮助文本改进

**时间分配（90分钟）：**
```
扫描 + 规划：15分钟
SPEC.md 拆分：45分钟
CLI 改进：20分钟
验证 + 收尾：10分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **多个相关 commit** — 不要为了"快速闭环"只做一个 PR
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution

---

**下次更新：** 下一轮 cron 执行后（2026-05-03）
