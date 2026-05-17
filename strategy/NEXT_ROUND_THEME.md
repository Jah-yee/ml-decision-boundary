# NEXT_ROUND_THEME.md — ml-decision-boundary v13

**更新时间：** 2026-05-17 22:05 CST
**版本：** v13 (安全修复 + v3 DoD 冲刺平台化)
**维护人：** 太子

---

## 📋 当前阶段状态

### v1 DoD（已完成 ✅）
- [x] pytest 覆盖率 ≥ 80%（当前 89%）
- [x] API 端点全测试覆盖（19个测例）
- [x] benchmark 命令标准化
- [x] 安全修复（traceback.format_exc() 移除）
- [x] REPRODUCE.md 新建

### v2 DoD（已完成 ✅）
- [x] pip-compile / pip-lock 流程 ✅ (2026-05-02)
- [x] Tree depth 敏感性测试矩阵 ✅ (2026-05-01 evening)
- [x] v1 → v2 阶段升级 ADR ✅ (ADR-0002, PR#18)
- [x] SPEC.md 拆分 ✅ (PR#19, 2026-05-03)
- [x] CLI 帮助文本改进 ✅ (2026-05-05: main.py argparse + benchmarks/run.py --help epilog)
- [x] GitHub Actions CI 配置 ✅ (PR#21, 2026-05-06)
- [x] CONTRIBUTING.md 完善 ✅ (PR#21, 2026-05-06)

### v3 DoD（进行中，剩余1项）
- [x] benchmark 报告 HTML 化 ✅ (PR#26, 2026-05-11)
- [x] GradientBoostingClassifier (GB) 支持 ✅ (PR#25, 2026-05-11)
- [x] Naive Bayes (NB) + GB API 层支持 ✅ (PR#27, 2026-05-12)
- [x] ExtraTrees (ET) + AdaBoost (AB) 支持 ✅ (PR#28, 2026-05-14)
- [x] 新数据集 s_curve 支持 ✅ (PR#31, 2026-05-15)
- [x] 超参调优实验体系基础设施 ✅ (PR#34, 2026-05-17)
- [x] 安全修复：web server traceback 暴露 ✅ (PR#35, 2026-05-17)
- [ ] **CLI/Web/API 平台化** ← v3 唯一剩余项

### v3 升级判定
**当前状态**: 6/7 完成（hyperparam sweep infra + s_curve + 安全修复）
**剩余项**: CLI/Web/API 平台化（需要更多工作才能完成）
**升级到 v4 入口条件**: CLI/Web/API 平台化完成 + ADR-0004

---

## ✅ 本轮完成（2026-05-17 晚间场）

### 安全修复：web server traceback 暴露
**问题**: `web/server.py` 的 `/train` 端点错误处理暴露完整 traceback，泄露内部路径、依赖版本等敏感信息
**修复**: 移除 `traceback.format_exc()`，仅返回 `str(e)`
**PR**: PR#35 ✅ Created + Pushed

### Hyperparam sweep 完整运行
- Total: 228 | Passed: 206 | Regressions: 22
- Avg accuracy: 0.8161
- 回归项分析：gamma=0.01 对 SVM 在 circles/xor 上造成显著 accuracy drop（预期行为）

### 下轮待办
1. 继续 v3 DoD: CLI/Web/API 平台化
2. web/server.py make_blobs 与 main.py 一致性修复（次优先级）
3. REPRODUCE.md 更新最后验证日期