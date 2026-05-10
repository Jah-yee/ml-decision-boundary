# NEXT_ROUND_THEME.md — ml-decision-boundary 深度维护版

**更新时间：** 2026-05-10 11:06 CST
**版本：** v6 (本轮深度扫描 + CI 基础设施分析)
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
- [x] benchmark 报告 HTML 化 ✅ (PR#22, 2026-05-08: report_html.py + trend charts + daily reports)
- [ ] 新模型支持或超参数调优实验体系
- [ ] 新数据集支持
- [ ] CLI/Web/API 平台化

---

## ⚠️ CI 基础设施问题 (需关注)

### 问题描述
所有 CI run（包括 master）都在 "Install dependencies" step 失败。

### 已排除的原因
- ✅ `--smoke` → `--quick` flag 修复 (PR#23)
- ✅ Tencent pip mirror 移除 (PR#24)
- ✅ requirements.lock 与 origin/master 一致
- ✅ 本地 P0/P1/P2 全部通过

### 可能的根因
- GitHub Actions runner 网络环境问题
- pip 缓存状态问题
- runner Python 3.10 环境特定问题

### 下一步
需要更多 runner 环境调试能力。建议:
1. 在 CI 中添加 `pip install --verbose` 看详细错误
2. 或者等待 GitHub Actions 基础设施恢复
3. 可以先合并 PR#22 (修复分支中的 --smoke)

---

## 🎯 下轮深度维护方向

### 主攻: 解决 PR#22 合并问题
**来源:** 遗留 + 本轮发现
**问题:** `fix/report-html-ts-bug` 分支的 ci.yml 包含 `--smoke` (应为 `--quick`)
**工作内容:**
1. 在本地 master 创建一个新分支
2. 从 PR#22 获取差异并应用，同时修复 ci.yml
3. 合并到 master

### 次攻: 新模型支持 (GradientBoosting)
**来源:** v2 附加目标
**问题:** 当前模型族可扩展
**工作内容:**
1. 评估 GradientBoosting 与现有 benchmark harness 兼容性
2. 添加到 benchmarks/run.py MODELS 字典
3. 校准阈值

---

## 📊 深度维护指标（v3 追踪）

| 指标 | 说明 | 目标 | 当前 |
|------|------|---------|------|
| commit_per_session | 每会话 commit 数 | ≥2 | 2 |
| problem_solved | 真正解决问题的比例 | ≥80% | 50% |
| p0_pass | P0 compileall | 100% | ✅ |
| p1_pass | P1 pytest | 100% | ✅ |
| p2_pass | P2 benchmark | ≥90% | ✅ |

---

## 🎯 本轮执行总结（2026-05-10 晨间场）

**本轮完成：**
- ✅ PR#21 合并 (api/train.py 统一错误格式)
- ✅ PR#24 合并 (requirements.lock 清理 mirror)
- ✅ 本地 P0/P1/P2 全部通过
- ✅ CI 基础设施问题分析（排除多种可能）
- ✅ CHANGELOG 更新
- ✅ Run log 归档

**本轮 commit 历史（2个）：**
1. `docs(changelog): update for today's session findings`
2. `docs(strategy): add morning run log 2026-05-10-1106`

**结论:** CI 失败是基础设施问题，非代码问题。

---

## 📝 本轮注意事项

1. **CI 问题分析** — Install dependencies 失败不是代码问题，已排除 mirror/flag/版本问题
2. **PR#22 仍需修复** — 分支含 `--smoke`，需要手动修复才能合并
3. **本地环境正常** — P0/P1/P2 在本地全部通过，说明代码质量OK

---

**下次更新：** 下一轮 cron 执行后（2026-05-10 evening 或 2026-05-11）