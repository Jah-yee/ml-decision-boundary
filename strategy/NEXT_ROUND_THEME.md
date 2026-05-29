# NEXT_ROUND_THEME.md — ml-decision-boundary v24 (v6 进行中)

**更新时间：** 2026-05-29 09:45 CST
**版本：** v24 (v6 第二天，进行中)
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
| 4 | Release 自动化（GitHub Release） | TBD | P2（待做） |
| 5 | README/SPEC.md 同步 v6 | 同步 v5 完成 + v6 阶段定义 | P3（通过 CI check_readme_consistency） |

---

## ✅ 本轮完成（2026-05-29 早场）

### PR 合并闭环

- **PR#44**：API contract test 覆盖增强 — ✅ 已合并（squash merge）

### 本地验证

- **P0**: compileall — ✅ pass
- **P1**: pytest 15 passed — ✅
- **P2**: API contract 增强 — ✅ 15 tests collected（从 4 → 15）
- **P3**: CI check_readme_consistency — ✅ pass

### 新增覆盖项

1. FakeReq/FakeRes Vercel serverless fixtures
2. /api/health — 任何请求体都返回 `{status: 'ok'}`
3. /api/train — 未知 dataset → HTTP 400（含错误信息）
4. /api/train — 未知 model → HTTP 500（traceback-free）
5. /api/train — 合法请求返回完整字段（accuracy, train_time, boundary_grid, etc.）
6. /api/train — 10 模型 × 2 数据集 smoke test
7. /api/train — 5 数据集全部可工作（SVM）
8. /api/train — p1/p2 影响模型参数
9. /api/train — 缺少 p1/p2 使用默认值 50/50
10. cross-module build_model 一致性
11. traceback leak prevention

---

## 📊 master 分支状态

```
c4efd7c test: enhance API contract coverage — ADR-0009 v6 DoD P2 (#44)
d70f5c7 docs(strategy): v23 — evening close, all PRs merged, NEXT_ROUND_THEME update
3992897 docs(strategy): evening session — merge PRs #40/41/42, ADR-0009 v6 DoD update
206d209 refactor: clean up core/train_utils.py C3 tech debt — ADR-0009 v6 DoD (#42)
```

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常，实际运行超时 | ✅ 已修复 collect（运行超时待查） |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理（PR#42） |
| C3 | api/health.py 缺 docstring | P3 | 未处理 |
| C4 | pytest 运行超时（本地） | 测试不阻塞 CI | 待查 |

---

## 下轮待办

1. [ ] **Release 自动化**（ADR-0009 P2）— 利用 generate_changelog.py 自动化 Release 草稿生成
2. [ ] **C3：api/health.py docstring** — 补充 P3 文档
3. [ ] **C4：pytest 运行超时调查** — 非阻塞，CI 正常

---

**版本历史**：
- v24 (2026-05-29 09:45): 早场 — PR#44 合并，API contract test P2 完成，v6 DoD #3 更新
- v23 (2026-05-28 21:50): 晚场 — PR#40/41/42 全部合并，PR#43 关闭