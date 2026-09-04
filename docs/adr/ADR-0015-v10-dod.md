# ADR-0015 — v10 DoD 细化：API Enhancement & Interactive Web UI

**日期**: 2026-07-09
**状态**: ✅ Accepted（v54 早场 DoD #1-4 全部完成，等皇上最终 review）
**维护人**: 太子

---

## 背景

v9 Documentation, Examples & Registry UX（ADR-0014）已于 2026-07-08 完成并 Accepted。v9 聚焦于文档和示例，解决了**C8（文档不足）**和部分 **C9（Web UI 功能有限）**。

v10 主题定位为 **API Enhancement & Interactive Web UI**，在 v9 基础上继续打磨 C9，并扩展 API 能力，为后续平台化（v11）奠定接口基础。

---

## v10 主题

**API Enhancement & Interactive Web UI**

---

## v10 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | **API Model Detail Endpoint** | `GET /api/models/<name>` 返回模型元数据（参数范围、适用场景、默认参数） | P1 | ✅ |
| 2 | **API Dataset Listing Endpoint** | `GET /api/datasets` 返回可用数据集列表（含参数范围、复杂度标签） | P1 | ✅ |
| 3 | **Web UI: Model Comparison View** | 在 Web UI 新增多模型并排对比视图，可同时查看 2-3 个模型的决策边界 | P1 | ✅ |
| 4 | **Web UI: Parameter Presets** | 为 SVM/RF/KNN 等添加"快速预设"按钮（高精度/均衡/轻量三档），降低交互门槛 | P1 | ✅ |
| 5 | **ADR-0015 Accepted** | DoD #1-4 全部完成后，将 ADR-0015 状态更新为 Accepted | P0 | ✅ |

> DoD #1-4 全部完成：v53 晚场 (#1-2) + v54 早场 (#3-4) | commit 9f35c16 | PR #56

---

## 技术约束

- API 改动必须向后兼容，不破坏现有 `/api/health` 和 `/api/train` 契约
- Web UI 改动在 `web/` 目录内，不影响 CLI 和 core/ 模块
- 所有新增 endpoint 需要基本集成测试（至少 smoke test）
- ADR-0015 Accepted 后方可开始 v11 规划

---

## 验收标准

- [x] ADR-0015 状态: Accepted
- [x] P0: compileall + import smoke 通过 ✅
- [x] P1: pytest -q 通过（298 passed, 5 skipped）✅
- [x] API: `/api/models/<name>` + `/api/datasets` 返回 200 + 有效 JSON ✅
- [x] Web UI: model comparison 和 presets 在本地可演示 ✅

---

## 依赖

- 依赖 v9 完成（ADR-0014 Accepted）✅
- 无其他 phase 依赖

---

## 下一步（v11 方向，待 ADR-0015 Accepted 后规划）

- Multi-dataset expansion (swiss roll, make_classification 变体)
- Batch prediction API
- Experiment history UI
