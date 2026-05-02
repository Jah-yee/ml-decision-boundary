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
- [ ] v1 → v2 阶段升级 ADR
- [ ] SPEC.md 拆分

---

## 🎯 下一轮深度维护方向

### 主攻：v1 → v2 阶段升级 ADR
**来源：** v2 DoD
**问题：** 需要正式的架构决策记录阶段升级内容
**工作内容：**
1. 在 docs/adr/ 创建阶段升级 ADR
2. 记录 v2 交付内容和架构变化
3. 更新 phases.md

**估计时间：** 60分钟

### 次攻：CLI 帮助文本改进
**来源：** 中优先级待办池
**问题：** 当前 CLI 帮助文本可能不够清晰
**工作内容：**
1. 审查 main.py 和 benchmarks/run.py 的 CLI 帮助文本
2. 改进错误提示和使用示例
3. 确保所有子命令都有 docstring

**估计时间：** 30分钟

---

## 🔍 深度扫描待办池

### 高优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| v1 → v2 阶段升级 ADR | v2 DoD | 60分钟 | #5 |
| CLI 帮助文本改进 | 产品体验 | 30分钟 | #3 |
| SPEC.md 拆分 | spec/混杂 | 45分钟 | #5 |

### 中优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| v1 → v2 阶段升级 ADR | phases.md | 60分钟 | #5 |
| SPEC.md 拆分 | spec/混杂 | 45分钟 | #5 |
| CLI 帮助文本改进 | 产品体验 | 30分钟 | #3 |

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
- ✅ API 错误响应格式统一（PR#17, commit d03df11）
- ✅ pip-lock requirements.lock 生成（commit 2875a4c）
- ✅ DEPENDENCY_POLICY.md 待办勾销

**下一轮建议（专项深挖）：**
- 主攻：v1 → v2 阶段升级 ADR
- 次攻：CLI 帮助文本改进

**时间分配（120分钟）：**
```
扫描 + 规划：20分钟
ADR 写作：60分钟
CLI 改进：30分钟
验证 + 收尾：30分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **多个相关 commit** — 不要为了"快速闭环"只做一个 PR
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution

---

**下次更新：** 下一轮 cron 执行后
