# NEXT_ROUND_THEME

## 上轮遗留（必须处理）

- [ ] `pytest` 是否写入 `requirements.txt`（上轮发现，上轮未处理）
- [ ] `benchmarks/reports/2026-04-27.md` 尚未生成（上轮 P2 未完成）
- [ ] 新建 `spec/DEPENDENCY_POLICY.md`（上轮三事项之一）

## 本轮任务（2026-04-27 上午场/下午场统一入口）

### 任务A：日常维护（新工作）
- **主轴**： Harness v1 — 扩展测试覆盖 + API 集成测试
- **约束**：不改动核心 ML 逻辑；聚焦测试和数据契约
- **验收**：P1 pytest 扩展；P3 API health 测试通过；benchmark report 更新

### 任务B：上轮 PR 收尾置信度评估（必须先做）
在进入任务A之前，**必须先执行 PR 收尾评估**：

1. 查 GitHub 上 Jah-yee/ml-decision-boundary 所有 OPEN PR：
   ```bash
   gh pr list --state open --repo Jah-yee/ml-decision-boundary --json number,title,url,state,reviewDecision,updatedAt
   ```

2. 对每条 PR 做五维置信度评分（0-2 分/维，总分 10 分）：
   - 代码质量 / 必要性 / 维护者响应 / 冲突风险 / 时效性

3. 决策：
   - ≥8 分 → **立即 merge**（高置信）
   - 5-7 分 → **继续等**，记录原因
   - <5 分 → **礼貌关闭**，附原因

4. 将评估结果写入 strategy/runs/YYYY-MM-DD-HHMM.md 的「PR收尾评估」小节

### 本轮验收层级
- P0：必须（compileall）
- P1：pytest 扩展覆盖
- P2：生成 benchmarks/reports/YYYY-MM-DD.md
- P3：API health smoke test 通过
