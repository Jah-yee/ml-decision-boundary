# NEXT_ROUND_THEME.md — ml-decision-boundary v23 (v6 进行中)

**更新时间：** 2026-05-28 21:50 CST
**版本：** v23 (v6 第一天，进行中)
**维护人：** 太子

---

## 📋 当前阶段状态

| Phase | 状态 | 完成日期 |
|-------|------|----------|
| v0 Foundation | ✅ | 2026-04-26 |
| v1 Testing & Harness | ✅ | 2026-04-29 |
| v2 Model & Data Expansion | ✅ | 2026-05-06 |
| v3 Platform | ✅ | 2026-05-19 |
| v4 Reproducibility & Robustness | ✅ | 2026-05-24 |
| v5 Automation & Documentation | ✅ | 2026-05-27 |
| v6 Stability & Extensibility | 进行中 | 2026-05-28（启动） |

---

## v6 DoD（来自 ADR-0009）

| # | DoD 项目 | 验证标准 | 状态 |
|---|---------|---------|------|
| 1 | respx/httpx 本地 env 冲突修复 | pytest collect 正常（本地 env issue） | ✅ 已修复（卸载 respx） |
| 2 | core/train_utils.py build_model 重复定义清理 | 文件无重复 def，从 192→140 行 | ✅ 已完成（PR#42 merged） |
| 3 | API contract test 覆盖增强 | TBD | P2（待做） |
| 4 | Release 自动化（GitHub Release） | TBD | P2（待做） |
| 5 | README/SPEC.md 同步 v6 | 同步 v5 完成 + v6 阶段定义 | P3（PR#43 关闭，内容已被 PR#42 覆盖） |

---

## ✅ 本轮完成（2026-05-28 晚场）

### PR 合并闭环

- **PR#40**：v5→v6 升级 docs — ✅ 已合并
- **PR#41**：main.py 数据集去重 — ✅ 已合并（rebase master 解决冲突）
- **PR#42**：train_utils dedup + ADR-0009 — ✅ 已合并（rebase master 解决冲突）
- **PR#43**：README/SPEC sync — ⚠️ 已关闭（内容与 PR#42 重复）

### 本地环境验证

- **P0**: compileall — ✅ pass
- **P1**: pytest collect — ✅ 216 tests collected
- **P2**: benchmark smoke — ✅ SVM/circles acc=0.9500

---

## 📊 master 分支状态

```
3992897 docs(strategy): evening session — merge PRs #40/41/42, ADR-0009 v6 DoD update
206d209 refactor: clean up core/train_utils.py C3 tech debt — ADR-0009 v6 DoD (#42)
9566832 refactor: delegate dataset generation to core/datasets.py (#41)
e645749 docs: phase v5→v6 upgrade — ADR-0008 + phases.md update (#40)
```

所有 open PR 已合并 ✅

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常，实际运行超时 | ✅ 已修复 collect（运行超时待查） |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | 未处理 |
| C4 | pytest 运行超时（本地） | 测试不阻塞 CI | 待查 |

---

## 下轮待办

1. [ ] **API contract test 覆盖增强**（ADR-0009 P2）— 基于现有 /train 和 /health 端点补充边界测试
2. [ ] **Release 自动化**（ADR-0009 P2）— 利用 generate_changelog.py 自动化 Release 草稿生成
3. [ ] **README/SPEC.md 最终同步检查**（ADR-0009 P3）— 确认 v5/v6 更新已同步
4. [ ] **pytest 运行超时调查**（C4）— 非阻塞，CI 正常

---

**版本历史**：
- v23 (2026-05-28 21:50): 晚场 — PR#40/41/42 全部合并，PR#43 关闭
- v22 (2026-05-28 21:47): PR#40/41 合并，PR#42 rebase 冲突解决
- v22 (2026-05-28 10:20): v6 启动，ADR-0009 完成，PR#42 open
- v21 (2026-05-27 22:15): main.py 去重完成，v5 全部完成，v6 启动