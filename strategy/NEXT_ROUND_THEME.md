# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**更新时间：** 2026-05-01 14:00 CST
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
- [ ] pip-compile / pip-lock 流程
- [x] Tree depth 敏感性测试矩阵 ✅ (2026-05-01 evening)
- [ ] v1 → v2 阶段升级 ADR
- [ ] SPEC.md 拆分

---

## 🎯 本轮深度维护方向

### 主攻：pip-lock 验证
**来源：** v2 DoD 遗留
**问题：** DEPENDENCY_POLICY.md 要求 pip-compile 流程，但尚未执行过验证
**工作内容：**
1. 运行 pip-compile 生成 requirements.txt / requirements-dev.txt
2. 验证 venv 中安装的包与 locked 文件一致
3. 确认 CI 环境与本地环境一致

**估计时间：** 30分钟（快速闭环）

### 次攻：API 错误响应格式统一
**来源：** THREAT_MODEL.md
**问题：** api/train.py 的错误响应格式不统一，可能泄露内部路径信息
**工作内容：**
1. 审查 api/train.py 所有 except 分支的错误响应
2. 统一为 `{error: string, code: string}` 格式
3. 确保不泄露 traceback / file path

**估计时间：** 45分钟（可深度挖掘）

---

## 🔍 深度扫描待办池

### 高优先级
| 待办 | 来源 | 估计时间 | 分叉 |
|------|------|---------|------|
| pip-lock 验证 | DEPENDENCY_POLICY | 30分钟 | #5 |
| API 错误响应格式统一 | THREAT_MODEL | 45分钟 | #3 |
| REPRODUCE.md 添加 Tree depth 注意 | research发现 | 20分钟 | #2 |

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

### 会话类型：专项深挖（主模式）

**适合原因：**
- Tree depth 矩阵是一个需要3个commit才能完整交付的工作
- commit 1: 扩展 benchmark 矩阵代码
- commit 2: 运行实验 + 记录结果
- commit 3: research 文档 + 结论分析

**时间分配（120分钟）：**
```
扫描 + 规划：20分钟
benchmark 矩阵代码：45分钟
运行实验：30分钟
research 文档：20分钟
验证 + 收尾：15分钟
缓冲：10分钟
```

---

## ⚠️ 本轮注意事项

1. **research 文档不是必做** — 只有真正有发现才写，不要硬造
2. **多个相关 commit** — 不要为了"快速闭环"只做一个 PR
3. **深度扫描前置** — 先扫描再规划，不要带着预设进项目
4. **karpathy-claude.md 四原则** — Think Before Coding, Simplicity First, Surgical Changes, Goal-Driven Execution

---

**下次更新：** 下一轮 cron 执行后
