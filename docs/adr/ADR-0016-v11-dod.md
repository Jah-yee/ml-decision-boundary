# ADR-0016 — v11 DoD 细化：Multi-Dataset Expansion & Experiment History

**日期**: 2026-07-10
**状态**: 🟡 Draft
**维护人**: 太子

---

## 背景

v10 API Enhancement & Interactive Web UI（ADR-0015）已于 2026-07-10 完成并 Accepted。v10 聚焦于 API 元数据端点和交互式 Web UI（对比视图 + 预设参数）。

v11 主题定位为 **Multi-Dataset Expansion & Experiment History**，扩展数据集支持、增加批预测 API，并建立实验历史追踪能力，为平台化成熟度奠定数据层基础。

---

## v11 主题

**Multi-Dataset Expansion & Experiment History**

---

## v11 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | **Multi-Dataset Support** | 新增 swiss_roll 数据集 + make_classification 变体（2-blobs, concentric），并在 API/Web UI 可选 | P1 | ✅ |
| 2 | **Batch Prediction API** | `POST /api/predict/batch` 端点，支持批量推理请求（JSON array in, JSON array out） | P1 | ✅ |
| 3 | **Experiment History UI** | 在 Web UI 新增历史实验面板，展示历史训练记录（模型、数据集、准确率、时间戳） | P1 | ✅ |
| 4 | **ADR-0016 Accepted** | DoD #1-3 全部完成后，将 ADR-0016 状态更新为 Accepted | P0 | 🟡 待皇上批准 |

---

## 技术约束

- Dataset 扩展必须向后兼容，不破坏现有 circle/moons/blobs 契约
- Batch Prediction API 需要请求校验（至少类型 + 非空检查）
- Experiment History 数据持久化到 `output/experiments.jsonl`（append-only log）
- ADR-0016 Accepted 后方可开始 v12 规划

---

## 验收标准（DoD #4 完成后勾选）

- [x] ADR-0016 状态: Draft
- [x] P0: compileall + import smoke 通过 ✅ (v56 早场)
- [x] P1: pytest -q 通过 ✅ 306 passed, 4 skipped
- [x] Dataset: swiss_roll 可加载 ✅ (v56 早场)
- [x] Dataset: classification_2blobs 可加载 ✅ (v56 早场)
- [x] Dataset: classification_concentric 可加载 ✅ (v56 早场)
- [x] API: `POST /api/predict/batch` 返回 200 + 有效 JSON array ✅ (v56 晚场)
- [x] Web UI: experiment history 面板显示历史记录 ✅ (v57 早场)
- [x] output/experiments.jsonl 正确写入实验历史 ✅ (v57 早场)

- [ ] ADR-0016 状态: Accepted 🟡 (请皇上批准)
- [ ] P0: compileall + import smoke 通过
- [ ] P1: pytest -q 通过
- [ ] Dataset: swiss_roll + make_classification 变体可加载
- [ ] API: `POST /api/predict/batch` 返回 200 + 有效 JSON array
- [x] Web UI: experiment history 面板显示历史记录 ✅
- [x] output/experiments.jsonl 正确写入实验历史 ✅

---

## 依赖

- 依赖 v10 完成（ADR-0015 Accepted）✅
- 无其他 phase 依赖

---

## 下一步（v12 方向，待 ADR-0016 Accepted 后规划）

- Deployment & Hosting（Vercel 部署配置更新）
- Multi-user / session management
- Export results as static HTML report
