# phases.md — 阶段定义

**版本**: v0.1 (Created 2026-04-26)

---

## v0 — Foundation (已完成 ✅)

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
- [x] P1: 测试基础设施（pytest>=7.0.0）
- [x] P1: 35 tests passed
- [x] P2: harness 可重复运行（固定 seed + JSON report schema）
- [x] P3: 集成测试（health check）

**v0 已完成 ✅ | v1 进行中**

---

## v1 — Testing & Harness (已完成 ✅)

---

## 当前阶段: v2 — Model & Data Expansion

**入口条件**: v1 DoD 全部完成 ✅

**本阶段 DoD**:
- [ ] SPEC.md 拆分（从 spec/ 目录移除混杂文件）
- [ ] CLI 帮助文本改进
- [ ] ADR-0002: Phase v1 → v2 升级判定 ✅ (2026-05-02)

**v0 已完成 ✅ | v1 已完成 ✅ | v2 进行中**

### v2 附加目标
- 扩展模型族（新增模型类型或超参数配置）
- 新数据集支持（更多合成数据场景）
- 模型超参数调优实验体系
- benchmark 报告自动化（HTML schema）

---

## 下一阶段: v3 — Platform

**目标**: 完整的 CLI/Web/API 平台化

---

## 阶段升级判定规则

- 每个 phase 的 P0 必须通过才能进入下一 phase
- phase 升级需要创建 `docs/adr/NNNN-phase-N-to-N+1.md`
- phase 之间禁止跳跃（必须顺序通过）
