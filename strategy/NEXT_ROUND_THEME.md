# NEXT_ROUND_THEME

## 本轮完成（2026-04-28 上午场）

- [x] `benchmarks/` 包创建 ✅（`__init__.py` + `__main__.py` + `run.py`）
- [x] `python3 -m benchmarks --quick` smoke test ✅（SVM/circles acc=0.79, threshold=0.70）
- [x] `python3 -m benchmarks` full suite ✅（52 exp, 45 passed, avg acc=0.8237）
- [x] `benchmarks/reports/2026-04-28.json` + `.md` 生成 ✅
- [x] v1 DoD: benchmark 命令标准化 → **完成** ✅
- [x] PR #5 已合并 ✅
- [x] `python3 -m compileall .` 无错误 ✅
- [x] `pytest -q` 28/28 passed ✅

---

## 上轮遗留（2026-04-27 下午场处理结果）

- [x] `spec/REPRODUCE.md` 检查（无需更新，内容正确）✅
- [x] v0→v1 阶段升级（通过 ADR-0001 正式记录）✅
- [x] benchmark 命令标准化（本轮完成）✅

---

## 下轮任务（2026-04-28 下午场）

### 任务：v1 Testing & Harness — 覆盖率提升

**主轴**：Harness 平台化（分叉#1）+ 模型与数据科学深化（分叉#2）

**约束**：不改动核心 ML 逻辑

**验收层级**：P0 / P1 / P2 / P3 全部维持通过

### v1 DoD（待推进）
- [ ] pytest 覆盖率 ≥ 80%（main.py 核心路径，当前 27%）
- [ ] API 端点全测试覆盖 ✅（7 个测例，test_api_contract.py）
- [ ] benchmark 命令标准化 ✅ **完成**

### 重点任务
1. **覆盖率提升**：为 `run_experiment` / `save_results` / `generate_comparison_plots` 等高价值函数添加测试用例，目标 80%+
2. **benchmark regression threshold 评估**：7 个失败案例分析（circles 上 linear SVM 0.43 / LR 0.36 / KNN 0.68 等），确认阈值是否合理
3. **负结果记录**：Tree(depth=3) 在 xor 上只有 0.46 准确率，写入 research/ 文档

### PR 状态
- 无 OPEN PR（本轮完成后将创建 1 个 PR）
- 置信度评估：N/A（本轮之前无 OPEN PR）

---

## 长期待办池（供参考）

- [ ] `pip-compile` 或 `pip-lock` 流程（来源：DEPENDENCY_POLICY 待办）
- [ ] `THREAT_MODEL.md`（每 3 轮至少检查一次）
- [ ] 监控 Vercel cold start 时间（当前 < 3s）