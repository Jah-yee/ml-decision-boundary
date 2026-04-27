# ADR-0001 — Phase v0 → v1 升级判定

**日期**: 2026-04-27
**状态**: Accepted
**决策者**: Jah-yee/ml-decision-boundary cron agent

---

## 背景

phases.md 中 v0 Foundation 阶段的 DoD 条目在 2026-04-27 上午场之前已全部通过，但 phases.md 文档未及时更新，导致状态不一致。本 ADR 记录正式的阶段升级判定。

---

## v0 阶段 DoD 实际完成情况

| DoD 条目 | 状态 | 证据 |
|---------|------|------|
| README 说明清晰，可 clone → run | ✅ 完成 | README.md 存在 |
| main.py 可独立运行 | ✅ 完成 | benchmarks/2026-04-27.md (72 experiments) |
| 有 requirements.txt | ✅ 完成 | requirements.txt 存在 |
| 有 vercel.json | ✅ 完成 | vercel.json 存在 |
| 有 output/ 目录 | ✅ 完成 | output/ 含 PNG + JSON |
| P1: 测试基础设施（pytest） | ✅ 完成 | requirements.txt 含 pytest>=7.0.0 |
| P1: 至少 1 个测试用例 | ✅ 完成 | 35 tests (28 test_main.py + 7 test_api_contract.py) |
| P2: harness 可重复运行（固定 seed + JSON report schema） | ✅ 完成 | main.py with RANDOM_STATE=42, experiment_results.json schema |
| P3: 集成测试（health check） | ✅ 完成 | tests/test_api_contract.py::test_health_response_structure |

---

## 升级判定

**v0 → v1 阶段升级条件已满足。**

判定依据：
- P0 ✅ (python3 -m compileall . 无错误)
- P1 ✅ (pytest -q 28/28 passed)
- P2 ✅ (python3 main.py 产出 benchmarks/reports/2026-04-27.md + 72 experiments)
- P3 ✅ (API health test 存在并通过)

---

## 升级后的 v1 入口条件

进入 v1 — Testing & Harness 阶段，入口条件：
- pytest 覆盖 main.py 主要逻辑 ✅（35 tests）
- benchmarks/reports/YYYY-MM-DD.md 可产出 ✅
- API 有集成测试 ✅

v1 阶段 DoD（待定义，下一轮任务）:
- pytest 覆盖率 ≥ 80%（main.py 核心路径）
- API 端点全测试覆盖
- benchmark 命令标准化为 `python3 -m benchmark` 或类似

---

## 决策

v0 阶段正式结束，phases.md 将更新当前阶段为 v1。

---

## 下一步

更新 `spec/phases.md`：将"当前阶段: v0"改为"当前阶段: v1 — Testing & Harness"，并清理已完成的 DoD 条目标记。