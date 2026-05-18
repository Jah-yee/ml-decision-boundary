# NEXT_ROUND_THEME.md — ml-decision-boundary v14

**更新时间：** 2026-05-18 09:55 CST
**版本：** v14 (core/ 模块提取 + 代码去重，平台化实质性推进)
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
- [x] **CLI/Web/API 平台化（代码去重）** ✅ (PR#36, 2026-05-18)
- [ ] **CLI/Web/API 平台化（剩余项）** ← v3 唯一剩余项

### v3 升级判定
**当前状态**: 7/8 完成
**剩余项**: CLI/Web/API 平台化剩余项（见下轮待办）
**升级到 v4 入口条件**: CLI/Web/API 平台化完成 + ADR-0004

---

## ✅ 本轮完成（2026-05-18 早间场）


### PR#36: core/ 模块提取 + 代码去重
**问题**: api/train.py 和 web/server.py 重复定义了9个相同函数（数据集生成器、模型工厂、参数转换等），共约360行重复代码。更存在静默bug：web/server.py的make_blobs接受3参数调用但只使用2参数。

**修复**:
- 新建 `core/datasets.py` (56行) — 5个数据集生成器集中管理
- 新建 `core/train_utils.py` (163行) — 4个ML工具函数集中管理
- api/train.py 从 ~224行 → 63行（移除160行重复代码）
- web/server.py 从 ~271行 → 100行（移除171行重复代码）
- 总计：+250行 / -361行

**关联v3 DoD**: CLI/Web/API 平台化 ✅（去重部分）

### 发现的剩余语义差异
**blobs数据集返回类别数不一致**:
- main.py: make_blobs(n, seed) → 2类（mask=y<2筛选）
- web/api: make_blobs(n, noise, seed) → 3类（noise被忽略，筛选被移除）
- 原因: DATASET_GENERATORS lambda中blobs的noise参数被静默忽略，导致行为与main.py不同
- 状态: 已记录，下轮需决定是否统一

### 下轮待办
1. v3 DoD剩余项: CLI/Web/API 平台化完整收尾
2. blobs语义差异修复（决定是否让web/api返回2类）
3. ADR-0004 创建（v3平台化正式ADR）
4. REPRODUCE.md 更新最后验证日期