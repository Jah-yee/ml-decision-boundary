# NEXT_ROUND_THEME.md — ml-decision-boundary v25 (v6 进行中)

**更新时间：** 2026-05-31 09:58 CST
**版本：** v25 (v6 第三天，进行中)
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
| 3 | API contract test 覆盖增强 | 15 new tests, 400/500 errors, traceback-free | ✅ 已完成（PR#44 merged） |
| 4 | Release 自动化（GitHub Release） | TBD | ✅ PR#45 created — awaiting CI |
| 5 | README/SPEC.md 同步 v6 | 同步 v5 完成 + v6 阶段定义 | P3（待处理） |

---

## ✅ 本轮完成（2026-05-31 早场）

### PR 创建闭环

- **PR#45**：`feat: release automation workflow + api/health.py docstring`
  - ADR-0009 v6 DoD #4：Release 自动化（.github/workflows/release.yml）
  - ADR-0009 v6 DoD #5（部分）：api/health.py docstring（C3 技术债务）
  - CI 待触发

### 本地验证

- **P0**: compileall — ✅ pass
- **P1**: pytest test_api_contract.py — ✅ 15 passed in 7.12s
- **P2**: benchmark smoke — ✅ circles/SVM acc=0.79 (threshold 0.70)
- **P3**: YAML syntax — ✅ validated

### 新增内容

1. `.github/workflows/release.yml`：GitHub Release 自动化 workflow
   - 触发条件：`v*` 标签
   - changelog 生成 via `generate_changelog.py`
   - Release 创建 via `softprops/action-gh-release@v2`
   - CHANGELOG.md 版本更新 via `stefanzweifel/git-auto-commit-action@v5`
2. `api/health.py`：完整 Google-style docstring（Args/Returns/Example）

---

## 📊 master 分支状态

```
f36ee1c docs(strategy): v24 — morning close, PR#44 merged, API contract P2 done
c4efd7c test: enhance API contract coverage — ADR-0009 v6 DoD P2 (#44)
d70f5c7 docs(strategy): v23 — evening close, all PRs merged, NEXT_ROUND_THEME update
```

### 待合并分支

```
feat/release-automation (PR#45) — v6 DoD #4 + #5 partial
```

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常，实际运行超时 | ✅ 已修复 collect |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理（PR#42） |
| C3 | api/health.py 缺 docstring | P3 | ✅ 已修复（PR#45） |
| C4 | pytest 运行超时（本地） | 测试不阻塞 CI | 待查（非阻塞） |

---

## 下轮待办

1. [ ] **PR#45 merge** — 等待 CI 通过后合并
2. [ ] **v6 DoD #5（剩余）：README/SPEC.md 同步 v6** — check_readme_consistency 已通过，P3
3. [ ] **C4：pytest 运行超时调查** — 非阻塞，CI 正常
4. [ ] **v6 完成标准评估** — DoD #1-4 全部完成后，评估是否进入 v7 规划

---

**版本历史**：
- v25 (2026-05-31 09:58): 早场 — PR#45 创建，v6 DoD #4 + C3 完成，v6 DoD #5 部分完成
- v24 (2026-05-29 09:45): 早场 — PR#44 合并，API contract test P2 完成，v6 DoD #3 更新
- v23 (2026-05-28 21:50): 晚场 — PR#40/41/42 全部合并，PR#43 关闭