# ADR-0017 — v12 DoD 细化：Python API & SDK Foundation

**日期**: 2026-10-07
**状态**: 🟡 Draft
**维护人**: 太子

---

## 背景

v11 Multi-Dataset Expansion & Experiment History（ADR-0016）已完成并 Accepted。v11 扩展了数据集支持、批预测 API 和实验历史追踪能力。

v12 主题定位为 **Python API & SDK Foundation**，为 ml-decision-boundary 建立清晰的 Python 编程接口，为外部集成和自动化流水线奠定基础。

---

## v12 主题

**Python API & SDK Foundation**

---

## v12 DoD 细化

| # | DoD 项目 | 描述 | 优先级 | 状态 |
|---|---------|------|--------|------|
| 1 | **Python SDK 接口** | 建立 `from ml_db import MLDB` 顶层 API，封装训练/预测/注册全流程 | P1 | 🟡 |
| 2 | **异步训练任务** | 后台训练任务 + 轮询状态 API，支撑长时间训练不被 HTTP 超时中断 | P1 | 🟡 |
| 3 | **Registry 改进** | 模型版本化（v1/v2）+ 标签批量查询（`--tag KEY`） | P1 | 🟡 |
| 4 | **ADR-0017 Accepted** | DoD #1-3 全部完成后，将 ADR-0017 状态更新为 Accepted | P0 | 🟡 |

---

## 技术约束

- Python SDK 必须向后兼容现有 CLI 接口
- 异步训练需要持久化任务状态（重启不丢失）
- Registry 版本化需要向后兼容 v1 模型 ID 格式
- ADR-0017 Accepted 后方可开始 v13 规划

---

## 验收标准（DoD #4 完成后勾选）

- [ ] ADR-0017 状态: Draft
- [ ] P0: compileall + import smoke 通过
- [ ] P1: pytest -q 通过
- [ ] SDK: `from ml_db import MLDB; m = MLDB()` 可实例化
- [ ] SDK: `m.train(...)` 返回训练结果
- [ ] SDK: `m.predict(...)` 返回预测结果
- [ ] Async: 后台任务状态可轮询
- [ ] Registry: 模型版本可查询
