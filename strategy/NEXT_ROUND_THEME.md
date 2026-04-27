# NEXT_ROUND_THEME

## 本轮完成（2026-04-27 上午场）

- [x] `pytest>=7.0.0` 已写入 `requirements.txt` ✅
- [x] `benchmarks/reports/2026-04-27.md` 已生成 ✅
- [x] `spec/DEPENDENCY_POLICY.md` 已创建 ✅
- [x] `tests/test_main.py` 扩展：+10 新测试（LR/NB/edge cases/ModelResult/API签名）✅
- [x] `pytest -q` 28/28 passed ✅
- [x] `python3 -m compileall .` 无错误 ✅

---

## 上轮遗留（2026-04-27 上午场处理结果）

- [x] `pytest` 写入 requirements.txt ✅
- [x] benchmarks/reports/2026-04-27.md 生成 ✅
- [x] spec/DEPENDENCY_POLICY.md 创建 ✅

---

## 下轮任务（2026-04-27 下午场）

### 任务：Harness v1 继续 — 测试矩阵完善 + REPRODUCE.md 更新

**主轴**：扩展测试覆盖 → 下一阶段：模型实验矩阵或 API 错误处理增强

**约束**：不改动核心 ML 逻辑

**验收层级**：P0 / P1 / P2 / P3 全部维持通过

### 待办
- [ ] `spec/REPRODUCE.md` 是否需要更新（P0 命令有变化？）
- [ ] 评估是否有更旧的遗留项需要处理
- [ ] 考虑下轮是否推进「模型与数据科学深化」（分叉#2）

### PR 状态
- 无 OPEN PR（本轮完成后将创建 1 个 PR）
- 置信度评估：N/A（本轮之前无 OPEN PR）

---

## 长期待办池（供参考）

- [ ] `pip-compile` 或 `pip-lock` 流程（防止传递依赖隐性升级）
- [ ] `THREAT_MODEL.md`（每 3 轮至少检查一次）
- [ ] 监控 Vercel cold start 时间（当前 < 3s）
- [ ] api/train.py 中 MLP max_iter 是否也需要从 500 提升到 2000（一致性）
