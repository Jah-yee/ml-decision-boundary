# NEXT_ROUND_THEME

## 本轮完成（2026-04-28 下午场）

- [x] `tests/test_experiment_flow.py` 新增（15 个测试：run_experiment 10 case + save_results 5 case）✅
- [x] `tests/test_benchmarks_smoke.py` 新增（8 个测试：CLI smoke + run module）✅
- [x] main.py coverage: 27% → **42%** (+15pp) ✅
- [x] TOTAL coverage: 42% → **60%** (+18pp) ✅
- [x] pytest: **58/58** passed（was 28）✅
- [x] benchmark full suite: 52 exp, 45 passed, 7 expected-fail ✅
- [x] `main.py` 修复：`save_results([])` 空列表 edge case ✅
- [x] `research/2026-04-28-negative-tree-on-xor.md` 负结果归档 ✅
- [x] PR #7 已合并 ✅
- [x] CHANGELOG.md 已更新 ✅
- [x] `python3 -m compileall .` 无错误 ✅

---

## 本轮处理结果（上午场遗留）

- [x] v1 Testing & Harness 覆盖率提升（本轮完成）✅
- [x] benchmark regression threshold 评估（写入 research 文档）✅
- [x] Tree(depth=3) on xor 负结果记录（0.46 准确率，已归档）✅

---

## 下轮任务（2026-04-29 上午场）

### 任务：v1 DoD 收尾 — 覆盖率向 80% 推进 + pip-lock 流程

**主轴**：治理与社区工程（分叉#5）+ Harness 平台化（分叉#1）

**约束**：不改动核心 ML 逻辑；不破坏现有 58 个测试

### v1 DoD（待推进）
- [x] pytest 覆盖率 ≥ 80%（当前 **60%**，还差 ~20pp）
- [x] API 端点全测试覆盖 ✅（7 个测例）
- [x] benchmark 命令标准化 ✅

### 重点任务
1. **覆盖率继续提升**：目标 80%+；当前缺失：main.py 的 `generate_comparison_plots`、`compute_decision_boundary`、`get_model_info`、`run_all_experiments`；benchmarks/run.py 覆盖率 22%
2. **pip-lock 流程**：DEPEDENCY_POLICY 待办（每轮检查一次），建立 locked requirements
3. **THREAT_MODEL.md**：每 3 轮至少检查一次（上轮跳过，本轮优先）

### 风险备注
- benchmark 7 个 expected-fail case 的 threshold 细粒度化需要推进（本轮已在 research 记录，下轮决定是否实施）

### PR 状态
- 无 OPEN PR（本轮完成）

---

## 长期待办池（供参考）

- [ ] `pip-compile` / `pip-lock` 流程（来源：DEPENDENCY_POLICY 待办）
- [ ] `THREAT_MODEL.md`（每 3 轮至少检查一次）
- [ ] Tree depth 敏感性测试矩阵（来源：本轮 research 建议）
- [ ] benchmark threshold 按 model×dataset 区分（来源：本轮 research 建议）
- [ ] 监控 Vercel cold start 时间（当前 < 3s）
