# ADR-0009 — v6 Stability & Extensibility: DoD 细化

**日期**: 2026-05-28
**状态**: Accepted
**决策者**: 太子

---

## 背景

v6（Stability & Extensibility）已进入阶段（由 ADR-0008 于 2026-05-27 升级判定）。

v6 阶段需在 v5 自动化基建之上，建立平台质量基线、清理残留技术债务、为可扩展性奠基。

---

## v6 DoD 候选项目

| # | DoD 项目 | 描述 | 优先级 |
|---|---------|------|--------|
| 1 | test_api_contract.py respx/httpx 依赖冲突修复 | 移除/替换 respx mock，恢复 pytest 可运行 | P1 |
| 2 | core/train_utils.py build_model 重复定义清理 | 文件无重复 def，从 192→140 行 | ✅ 已完成（PR#42 merged） |
| 3 | API contract test 覆盖增强 | 基于现有 `/train` 和 `/health` 端点补充边界测试 | P2 |
| 4 | Release 自动化（GitHub Release） | 利用 generate_changelog.py 自动化 Release 草稿生成 | P2 |
| 5 | 文档 v5/v6 更新至 README/SPEC | 同步 v5 完成项、v6 阶段定义至 README & SPEC | P3 |

---

## 排除项目

- 多语言 SDK（非目标）
- AutoML/超参搜索平台（非目标）
- 生产部署托管（非目标）
- respx 本地调试环境修复（env issue，CI 中不影响）

---

## 本次细化结果

| # | DoD 项目 | 来源 | 验证标准 |
|---|---------|------|---------|
| 1 | test_api_contract.py 修复 | respx env 冲突 | pytest 不再因 respx 失败 → P0 通过 |
| 2 | core/train_utils.py dedup | 本轮扫描发现 | `git show --stat` 无重复 def |
| 3 | v6 DoD ADR | ADR-0008 要求 | 本 ADR Accepted |

---

## 决策

**ADR-0009 Accepted**：v6 DoD 已细化，3 个候选项目进入执行队列。

---

**版本历史**：
- v1 (2026-05-28): Initial — v6 DoD 细化
