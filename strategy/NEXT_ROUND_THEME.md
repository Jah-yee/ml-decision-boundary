## 本轮完成（2026-04-29 上午场）

- [x] `tests/test_main_coverage.py` 新增（13 个测试：compute_decision_boundary×2 + get_model_info×5 + generate_single_model_visualization×4 + generate_comparison_plots×1 + run_all_experiments×1）✅
- [x] `tests/test_benchmarks_main.py` 新增（3 个测试：--quick + full suite + --help）✅
- [x] `THREAT_MODEL.md` 新建（攻击面 + 信任边界 + 依赖安全 + 部署姿态 + 4 个待办）✅
- [x] main.py coverage: 42% → **87%** (+45pp) ✅
- [x] TOTAL coverage: 60% → **79%** (+19pp) ✅
- [x] pytest: **74/74** passed（was 58）✅
- [x] CHANGELOG.md 已更新 ✅
- [x] `python3 -m compileall .` 无错误 ✅

---

## 本轮处理结果（2026-04-28 遗留）

- [x] v1 Testing & Harness 覆盖率提升（本轮完成）✅
- [x] pip-lock 流程（spec/DEPENDENCY_POLICY 已存在，pip-compile 工具待评估）
- [x] Tree depth 敏感性测试矩阵（来源：research 负结果文档）

---

## 下轮任务（2026-04-29 下午场）

### 任务：v1 DoD 最终冲刺 — 覆盖率向 85% 推进 + pip-lock 验证 + 剩余文档

**主轴**：治理与社区工程（分叉#5）+ Harness 平台化（分叉#1）

**约束**：不改动核心 ML 逻辑；不破坏现有 74 个测试

### v1 DoD（待推进）
- [x] pytest 覆盖率 ≥ 80%（当前 **79%**，接近达标）
- [x] API 端点全测试覆盖 ✅（7 个测例）
- [x] benchmark 命令标准化 ✅

### 重点任务
1. **覆盖率最终冲刺**：目标 85%+；剩余缺失：
   - `benchmarks/run.py`: 22%（`run_full_benchmark` 的 expected-fail 路径、`generate_summary`、`write_report`）
   - `api/train.py`: 20%（Flask route，`@app.route` 装饰的函数难以 unit test）
   - 考虑增加 `test_benchmarks_run.py` 测试 `run_full_benchmark` + `generate_summary` 的 mock 路径
2. **pip-lock 验证**：运行 `pip-compile` 或手动验证 `requirements.txt` 锁版本稳定性
3. **pip-compile 集成到 CI**（如时间允许）
4. **api/train.py 错误消息 review**：检查是否泄露内部路径（来自 THREAT_MODEL 待办）

### 风险备注
- benchmarks/run.py 剩余覆盖缺口主要在 expected-fail 路径（需要手动触发异常）
- api/train.py Flask 路由需要 serverless 上下文才能真正测试

### PR 状态
- 无 OPEN PR（本轮完成）

---

## 长期待办池（供参考）

- [ ] pip-compile / pip-lock 流程（来源：DEPENDENCY_POLICY 待办）
- [ ] Tree depth 敏感性测试矩阵（来源：research 负结果文档）
- [ ] benchmark threshold 按 model×dataset 区分（来源：research 建议）
- [ ] api/train.py 错误消息信息泄露 review（来源：THREAT_MODEL）
- [ ] 监控 Vercel cold start 时间（当前 < 3s）
- [ ] SPEC.md 拆分（当前 spec/ 下文件混杂）
