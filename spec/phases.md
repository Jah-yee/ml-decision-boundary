# phases.md — 阶段定义

**版本**: v0.1 (Created 2026-04-26)

---

## 当前阶段: v0 — Foundation（P0 可复现）

**入口条件**: 仓库可 clone、可 install requirements、可 `python3 main.py` 成功运行并产生 output/ 下的可视化文件。

**出口条件**: 
- P0 通过（compileall + import smoke）
- P1: 有测试基础设施（至少 conftest + 1 个测试用例）
- P2: `python3 main.py` 可执行，产生 JSON + PNG
- P3: API health 返回 200，Web 可本地启动

**本阶段 DoD**:
- [x] README 说明清晰，可 clone → run
- [x] main.py 可独立运行
- [x] 有 requirements.txt
- [x] 有 vercel.json
- [x] 有 output/ 目录

**待完成 DoD**:
- [ ] P1: 测试基础设施（pytest）
- [ ] P1: 至少 1 个测试用例
- [ ] P2: harness 可重复运行（固定 seed + JSON report schema）
- [ ] P3: 集成测试（health check）

---

## 下一阶段: v1 — Testing & Harness

**目标**: 建立完整的测试覆盖率和实验 harness

**入口条件**: v0 DoD 全部完成

**出口条件**:
- pytest 覆盖 main.py 主要逻辑
- benchmarks/reports/YYYY-MM-DD.md 可产出
- API 有集成测试

---

## 未来阶段: v2 — Model & Data Expansion

**目标**: 扩展模型族和数据集

---

## 未来阶段: v3 — Platform

**目标**: 完整的 CLI/Web/API 平台化

---

## 阶段升级判定规则

- 每个 phase 的 P0 必须通过才能进入下一 phase
- phase 升级需要创建 `docs/adr/NNNN-phase-N-to-N+1.md`
- phase 之间禁止跳跃（必须顺序通过）
