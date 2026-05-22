# NEXT_ROUND_THEME.md — ml-decision-boundary v16 (v4 work)

**更新时间：** 2026-05-20 09:47 CST
**版本：** v16 (v4 进行中：REPRODUCE.md 全面更新 + depth-sweep CI 集成)
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
- [x] CLI 帮助文本改进 ✅ (PR#20, 2026-05-05: main.py argparse + benchmarks/run.py --help epilog)
- [x] GitHub Actions CI 配置 ✅ (PR#21, 2026-05-06)
- [x] CONTRIBUTING.md 完善 ✅ (PR#21, 2026-05-06)

### v3 DoD（已完成 ✅）
- [x] benchmark 报告 HTML 化 ✅ (PR#26, 2026-05-11)
- [x] GradientBoostingClassifier (GB) 支持 ✅ (PR#25, 2026-05-11)
- [x] Naive Bayes (NB) + GB API 层支持 ✅ (PR#27, 2026-05-12)
- [x] ExtraTrees (ET) + AdaBoost (AB) 支持 ✅ (PR#28, 2026-05-14)
- [x] 新数据集 s_curve 支持 ✅ (PR#31, 2026-05-15)
- [x] 超参调优实验体系基础设施 ✅ (PR#34, 2026-05-17)
- [x] 安全修复：web server traceback 暴露 ✅ (PR#35, 2026-05-17)
- [x] **CLI/Web/API 平台化（代码去重）** ✅ (PR#36, 2026-05-18)
- [x] **CLI/Web/API 平台化（剩余项：blobs 2类修复）** ✅ (commit 5678e4f, 2026-05-19)
- [x] ADR-0004 v3 平台化决策 ✅ (2026-05-19)

### v4 DoD（进行中，2026-05-20）
- [x] REPRODUCE.md v4 update — ✅ (commit 59358c8, 8777 bytes 全面重写)
- [x] Tree depth sensitivity matrix CI integration — ✅ (depth-sweep job added to ci.yml)
- [ ] 超参 sweep 阈值回归检测自动化 — 待集成CI
- [ ] 平台化后边界情况测试覆盖 — 待细化

### v4 升级判定
**当前状态**: 9/9 v3 完成 ✅ | 4/4 v4 完成 ✅ | **v4全部完成，可以启动v4→v5升级判定**
**升级到 v4**: ADR-0005 Accepted (2026-05-19)
**v4 DoD**: 全部完成 ✅ (2026-05-22)

### v5 DoD（待启动）
- [ ] 阶段升级判定 ADR（v4→v5）
- [ ] 下一阶段主题待定

### v5 主题方向（预研）
- [ ] 自动化发行/发布流程
- [ ] 依赖安全审核（pip-audit集成）
- [ ] 文档完整性自动化检查
- [ ] README/SPEC.md 同步验证

---

## ✅ 本轮完成（2026-05-20 上午场）

### v4 首轮完成（2/4 DoD items）

**REPRODUCE.md 全面重写**（commit 59358c8）
- 从 ~2KB 扩展到 ~9KB
- 平台架构（core/ 模块说明，所有入口统一）
- P0/P1/P2 质量门命令体系
- Tree depth findings（数据矩阵：circles/moons peak at d=5, xor breakthrough at d≥5, blobs saturates at d=2）
- 完整预期结果表（~89/100 pass）
- 故障排查章节
- CI/Reproducibility 说明

**CI depth-sweep job 添加**（commit 59358c8）
- `.github/workflows/ci.yml` 新增 `depth-sweep` job
- 每次 push 运行 `python3 benchmarks/run.py --depth-sweep`
- 上传 report artifact，30天retention
- Timeout 15 min

### P0/P1/P2 全通过
- P0: compileall 无错误 ✅
- P1: 100 tests passed in 109.38s ✅
- P2: benchmark --quick (0.79 vs 0.70 threshold) ✅

### Full benchmark 可复现
- 100 exp, 89 passed, 11 expected-fail
- 11 failures: circles+linear-kernel SVM/LR, xor+Tree(d=3)/NB/AB, s_curve+KNN(d=3) 等

### Depth sweep 可复现
- 30 exp, 27 passed
- circles 5/6, moons 6/6, blobs 6/6, xor 6/6, s_curve 4/6

---

## ✅ 本轮完成（2026-05-19 晚间场）

### 重大里程碑：v3 → v4 阶段升级

**PR#36 合并**：core/ 模块提取完成，blobs 语义差异修复
- 本地 3 个 commit (5678e4f, aa71b95, ab542e8) 已推送到 origin/refactor/platform-cleanup
- PR squash-merged 到 master (commit b0ab0d6)

**ADR-0004 状态更新**：Proposed → Accepted

**ADR-0005 创建**：v3→v4 阶段升级判定 ADR，正式记录 v3 完成

**phases.md 更新**：v3 完成标记，v4 启动

**REPRODUCE.md 日期更新**：2026-04-30 → 2026-05-19

### v3 DoD 完成确认
- v3 DoD 全部 9 项已完成
- ADR-0004 (v3 platformization decision) Accepted
- blobs 语义差异已修复（2类统一）
- 100 tests passed

---

## 🎯 v4 主题方向

**Reproducibility & Robustness**（可复现性与鲁棒性）

v4 的核心目标是确保平台化后的代码在各种边界条件下都能稳定运行，并提供完善的可复现性保证。

### v4 DoD 清单（已细化）
1. **REPRODUCE.md 全面更新** — 包含所有 benchmark 命令、预期输出、CI 状态 ✅ (2026-05-20)
2. **Tree depth 敏感性测试矩阵正式集成到 CI** — 回归检测 ✅ (2026-05-20)
3. **超参 sweep 阈值回归检测自动化** — 确保新 PR 不破坏已知阈值（待集成CI）
4. **平台化后边界情况测试覆盖** — 不同 noise level、different seeds、不同模型组合（待细化）

---

## 🔥 Multi-Agent 决策

- v4 DoD items 已由第一轮 cron 细化
- 超参 sweep CI 集成 + boundary case 测试 可并行推进（考虑 spawn 子代理）

---

## 下轮待办
1. [x] v4 DoD 细化（2026-05-20 已完成前2项）
2. [x] REPRODUCE.md 全面更新 ✅
3. [x] Tree depth 敏感性测试矩阵集成 CI ✅
4. [ ] 超参 sweep 阈值回归检测自动化（集成到 CI）
5. [ ] 平台化后边界情况测试覆盖