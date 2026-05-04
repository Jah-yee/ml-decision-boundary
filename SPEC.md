# SPEC.md — ml-decision-boundary 核心规范

> **版本**: v1.0.0
> **更新时间**: 2026-05-03
> **维护人**: 太子

---

## 📁 文档结构

```
ml-decision-boundary/
├── SPEC.md              ← 本文件：核心规范入口
├── spec/
│   ├── CHARTER.md       ← 愿景、使命、质量门槛
│   └── phases.md        ← 阶段定义（v0/v1/v2/v3）
├── docs/
│   ├── AGENT_CRON_PLAYBOOK.md   ← Owner Agent 执行手册
│   ├── DEPENDENCY_POLICY.md      ← 依赖治理政策
│   ├── REPRODUCE.md              ← 可复现性指南
│   └── adr/                      ← 架构决策记录
├── api/                 ← API 实现
├── benchmarks/          ← benchmark 报告
├── main.py              ← CLI 入口
├── requirements.txt     ← 依赖（dev 环境）
├── requirements.lock    ← 锁定版本（生产环境）
└── tests/               ← 测例
```

---

## 🎯 项目概述

**名称**: ml-decision-boundary
**类型**: 自有产品 / ML 决策边界可视化工具
**核心功能**: 实时可视化不同 ML 模型如何划分特征空间

### 愿景
让 ML 模型的决策边界可视化，帮助理解模型行为和失败模式。

### 使命
提供可复现的实验平台，支持多模型、多数据集的对比分析。

### 非目标
- 不做 AutoML
- 不做模型压缩/优化
- 不做生产部署

---

## 📐 核心规范

### 1. 依赖治理
遵循 `docs/DEPENDENCY_POLICY.md` 规定的 P0/P1 分级。

### 2. 阶段演进
遵循 `spec/phases.md` 定义的 v0 → v1 → v2 → v3 阶段路线图。

### 3. 可复现性
所有实验必须可通过 `docs/REPRODUCE.md` 中的命令复现。

### 4. 安全
- 禁止在错误响应中暴露 traceback
- 禁止硬编码 secrets
- 依赖变更必须通过 pip-compile 审核

---

## 🔄 变更记录

| 版本 | 日期 | 变更 |
|------|------|------|
| v1.0.0 | 2026-05-03 | 初始版本：文档结构调整（spec/ → docs/） |