# NEXT_ROUND_THEME.md — ml-decision-boundary v8

**更新时间：** 2026-05-14 09:42 CST
**版本：** v9 (ET/AB 模型支持合并，PR#28)
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

### v3 DoD（进行中）
- [x] benchmark 报告 HTML 化 ✅ (PR#26, 2026-05-11)
- [x] GradientBoostingClassifier (GB) 支持 ✅ (PR#25, 2026-05-11)
- [x] Naive Bayes (NB) + GB API 层支持 ✅ (PR#27, 2026-05-12)
- [x] ExtraTrees (ET) + AdaBoost (AB) 支持 ✅ (PR#28, 2026-05-14)
- [ ] 新数据集支持
- [ ] 超参数调优实验体系
- [ ] CLI/Web/API 平台化

---

## ✅ 本轮完成（2026-05-11 晨间场）

### CI 基础设施根本修复
**问题根因：** requirements.lock 中依赖版本超出 GitHub Actions runner Python 3.10 支持范围
**修复：** 降级所有 CI 不兼容的包版本

| 包 | 旧版本 | 新版本 | 原因 |
|----|--------|--------|------|
| matplotlib | 3.10.9 | 3.7.5 | 3.10+ requires Python ≥3.11 |
| scipy | 1.17.1 | 1.11.4 | 1.17+ requires Python ≥3.11 |
| scikit-learn | 1.8.0 | 1.7.2 | 1.8+ requires Python ≥3.11 |
| contourpy | 1.3.3 | 1.3.2 | 1.3.3 requires Python ≥3.11 |
| numpy | 2.4.4 | 1.26.4 | 2.4+ requires Python ≥3.11 |

### PR 合并
- **PR#25** ✅ Merged — GradientBoostingClassifier (GB) 支持
- **PR#26** ✅ Merged — Backport of PR#22 (HTML reports + depth sweep) with fixed requirements.lock
- **PR#22** 🔴 Closed — 内容已迁移到 PR#26

### CI 改进
- 迁移 `actions/setup-python@v5` 内置 pip cache（移除 `actions/cache@v4`）
- 添加 `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24` 环境变量（避免 Node.js 20 弃用警告）
- 添加 `persist-credentials: false` 到 checkout（安全最佳实践）

---

## 🎯 下轮深度维护方向

### 主攻: v3 DoD 剩余项
1. **新模型支持** — 评估更多模型（ExtraTrees, AdaBoost, etc.）
2. **新数据集支持** — 添加更多数据集变体
3. **平台化** — CLI/Web/API 标准化

### 次攻: CI 缓存优化
- 验证新 pip cache 机制是否命中
- 监控 CI 执行时间变化

---

## 📊 深度维护指标（v3 追踪）

| 指标 | 说明 | 目标 | 当前 |
|------|------|---------|------|
| commit_per_session | 每会话 commit 数 | ≥2 | 4 |
| problem_solved | 真正解决问题的比例 | ≥80% | 80% |
| p0_pass | P0 compileall | 100% | ✅ |
| p1_pass | P1 pytest | 100% | ✅ |
| p2_pass | P2 benchmark | ≥90% | ✅ |

---

## 📝 本轮注意事项

1. **requirements.lock 必须用 pip-compile 在目标 Python 版本生成** — 本地 Python 3.12 与 CI Python 3.10 版本差异导致包版本溢出
2. **PR#22 迁移方式** — 从 origin/fix/report-html-ts-bug 手动提取内容，创建新分支应用，自建 PR 合并
3. **CI 环境变量** — `FORCE_JAVASCRIPT_ACTIONS_TO_NODE24=true` 可在 workflow 文件中提前避免 Node.js 20 停用警告

---

## ✅ 本轮完成（2026-05-14 晨间场）

### ET/AB 模型支持
- api/train.py: 添加 ExtraTrees (ET) 和 AdaBoost (AB) 到 build_model/slider_to_params/get_model_info_dict
- web/server.py: 同步添加 ET 和 AB 支持
- P0: compileall + import smoke ✅
- P1: 100 tests passed (82.89s) ✅
- P2: benchmarks/quick pass (SVM circles acc=0.79) ✅

### PR 合并
- **PR#28** ✅ Merged — ET/AB 模型支持 (squash merge)

### 运行日志
- strategy/runs/2026-05-14-0942.md

---

## ✅ 本轮完成（2026-05-12 晚间场）

### 修复 Push 认证问题 (GH007)
**问题根因：** 本地 .gitconfig 配置了私人邮箱 `jydu_seven@outlook.com`，GitHub 阻止发布到 public repo
**修复：** 改用 GitHub noreply address `166608075+Jah-yee@users.noreply.github.com`

### NB/GB API 层支持
- api/train.py: 添加 GaussianNB 和 GradientBoostingClassifier 到 build_model/slider_to_params/get_model_info_dict
- web/server.py: 同步添加 GB 和 NB 支持
- P0: compileall + import smoke ✅
- P1: 8 models 冒烟测试全部通过 ✅
- P2: benchmarks/run.py --quick 通过 ✅

### PR 合并
- **PR#27** ✅ Merged — NB/GB API 层支持 (squash merge)

### 运行日志
- strategy/runs/2026-05-12-2157.md

---

## ✅ 本轮完成（2026-05-11 晨间场）

### CI 基础设施根本修复
**问题根因：** requirements.lock 中依赖版本超出 GitHub Actions runner Python 3.10 支持范围
**修复：** 降级所有 CI 不兼容的包版本