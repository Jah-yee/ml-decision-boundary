# ADR-0005 — Phase v3 → v4 升级判定

**日期**: 2026-05-19
**状态**: Accepted
**决策者**: Jah-yee <jydu_seven@outlook.com>

---

## 背景

v3 Platform 阶段的 DoD 要求 CLI/Web/API 平台化。PR#36 (core/ 模块提取) 已合并，ADR-0004 已更新为 Accepted。本文档记录 v3 → v4 的正式升级判定。

### v3 DoD 完成状态（2026-05-19）

| DoD 项 | 状态 | 关联 PR |
|--------|------|---------|
| benchmark 报告 HTML 化 | ✅ | PR#26 (2026-05-11) |
| GradientBoostingClassifier (GB) 支持 | ✅ | PR#25 (2026-05-11) |
| Naive Bayes (NB) + GB API 层支持 | ✅ | PR#27 (2026-05-12) |
| ExtraTrees (ET) + AdaBoost (AB) 支持 | ✅ | PR#28 (2026-05-14) |
| 新数据集 s_curve 支持 | ✅ | PR#31 (2026-05-15) |
| 超参调优实验体系基础设施 | ✅ | PR#34 (2026-05-17) |
| 安全修复：web server traceback 暴露 | ✅ | PR#35 (2026-05-17) |
| CLI/Web/API 平台化（代码去重） | ✅ | PR#36 (2026-05-19) |
| CLI/Web/API 平台化剩余项（blobs 语义差异） | ✅ | commit 5678e4f (2026-05-19) |

**v3 DoD: 9/9 完成 ✅**

### ADR-0004 状态

- ADR-0004 (v3 platformization decision) 已创建，内容为 `core/` 模块提取方案
- PR#36 合并后状态已更新为 `Accepted`

---

## 决策

### 升级判定：v3 → v4

**结论**: 满足全部升级条件，批准进入 v4 阶段。

### 升级证据

1. **v3 DoD 9/9 完成** — 见上表
2. **ADR-0004 Accepted** — PR#36 merged, ADR status updated
3. **P0 验证通过** — `python3 -m compileall .` 无错误
4. **P1 验证通过** — 100 tests passed
5. **blobs 语义差异已修复** — commit 5678e4f normalizes blobs to 2-class binary classification

---

## v4 入口条件

v4 阶段主题：**可复现性与鲁棒性**。

v4 DoD 候选方向（待 v4 启动后细化）：
- [ ] REPRODUCE.md 全面更新（包含所有 benchmark 命令 + 预期输出）
- [ ] Tree depth 敏感性测试矩阵正式集成到 CI
- [ ] 超参 sweep 阈值回归检测自动化
- [ ] 平台化后的边界情况测试覆盖（blobs/xor/s_curve 不同 noise level）
- [ ] ADR-0005 正式记录 v3 完成

---

## 不做（明确）

- v4 的具体 DoD 由 v4 阶段第一轮 cron 决定（ADR-0005 记录升级判定，不定义 v4 范围）
- v4 的技术决策（如超参实验报告格式）不在本 ADR 范围内

---

**历史**：
- 2026-05-19: Created (Accepted) — v3 DoD 9/9 完成 + ADR-0004 merged