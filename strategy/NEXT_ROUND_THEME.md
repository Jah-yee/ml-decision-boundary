# NEXT_ROUND_THEME

## 本轮完成（2026-04-27 下午场）

- [x] ADR-0001 创建 ✅ (`docs/adr/ADR-0001-phase-v0-to-v1.md`)
- [x] `spec/phases.md` v0.2 更新 ✅（v0 标记完成，v1 DoD 新增）
- [x] CHANGELOG.md 更新 ✅
- [x] PR #4 已合并 ✅
- [x] `python3 -m compileall .` 无错误 ✅
- [x] `pytest -q` 28/28 passed ✅

---

## 上轮遗留（2026-04-27 下午场处理结果）

- [x] `spec/REPRODUCE.md` 检查（无需更新，内容正确）✅
- [x] v0→v1 阶段升级（通过 ADR-0001 正式记录）✅

---

## 下轮任务（2026-04-28 上午场）

### 任务：v1 Testing & Harness — 继续推进 DoD

**主轴**：Harness 平台化（分叉#1）+ 治理工程（分叉#5）

**约束**：不改动核心 ML 逻辑

**验收层级**：P0 / P1 / P2 / P3 全部维持通过

### v1 DoD（待推进）
- [ ] pytest 覆盖率 ≥ 80%（main.py 核心路径）
- [ ] API 端点全测试覆盖
- [ ] benchmark 命令标准化为 `python3 -m benchmark` 或类似

### 备选任务
- [ ] 推进「模型与数据科学深化」（分叉#2）：新增模型族或评估协议

### PR 状态
- 无 OPEN PR（本轮完成后将创建 1 个 PR）
- 置信度评估：N/A（本轮之前无 OPEN PR）

---

## 长期待办池（供参考）

- [ ] `pip-compile` 或 `pip-lock` 流程（来源：DEPENDENCY_POLICY 待办）
- [ ] `THREAT_MODEL.md`（每 3 轮至少检查一次）
- [ ] 监控 Vercel cold start 时间（当前 < 3s）