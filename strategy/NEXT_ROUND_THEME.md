# NEXT_ROUND_THEME.md — ml-decision-boundary v28 (v7 DoD #1 完成 ✅)

**更新时间：** 2026-06-02 09:50 CST
**版本：** v28 (v7 DoD #1 完成，早场)
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
| v6 Stability & Extensibility | ✅ 完成 | 2026-05-31 |
| v7 Extensibility, Edge Cases & UX | 🔄 进行中 | 2026-06-02 |

---

## v7 DoD（来自 ADR-0011）— 进行中

| # | DoD 项目 | 状态 |
|---|---------|------|
| 1 | 自定义模型插件接口 | ✅ PR#50 merged |
| 2 | 数据集边界验证 | ⏳ 待启动 |
| 3 | 错误信息改进 | ⏳ 待启动 |
| 4 | C4: pytest 超时修复 | ⏳ 待启动 |
| 5 | ADR-0011 更新同步 | ⏳ 待完成 |

---

## ✅ 本轮完成（2026-06-02 早场）

### PR 创建闭环

- **PR#50**：`feat(core/plugins): implement custom model plugin interface — v7 DoD #1`
  - `core/interfaces.py` — ModelBuilder 抽象接口
  - `core/plugins/registry.py` — 插件发现与注册
  - `core/plugins/models/svm_plugin.py` — SVM 插件示例
  - `core/train_utils.py` — build_model() 插件感知，未知模型错误更友好
  - `tests/test_plugins.py` — 15 个测试用例

### 本地验证

- **P0**: compileall — ✅ pass
- **P0**: import main — ✅ OK
- **P1**: test_plugins.py — ✅ 15 passed
- **P1**: test_api_contract.py — ✅ 15 passed (7s)

### v7 DoD #1 完成判定

> ADR-0011 DoD #1 全部验收标准满足 ✅
> 插件系统可正常工作，SVM 可通过插件加载 ✅
> PR#50 已 merge ✅

---

## 📊 master / daily 分支状态

```
master:  251c509 docs: phase v6→v7 upgrade — ADR-0010
daily/v7-evening-adr0011: 727ccab feat(core/plugins): implement custom model plugin interface (#50)
```

---

## 技术债务

| # | 问题 | 影响 | 状态 |
|---|------|------|------|
| C1 | respx/httpx 本地 env 冲突 | pytest collect 正常 | ✅ 已修复 |
| C2 | core/train_utils.py 重复 def | 死代码 | ✅ 已清理 |
| C3 | api/health.py 缺 docstring | P3 | ✅ 已修复 |
| C4 | pytest 运行超时（本地） | 非阻塞 | 待查 |

---

## 下轮主题（v28 晚场）

**主题**：v7 DoD #2 — 数据集边界验证

**待办**：
1. [ ] **ADR-0011 更新为 Accepted** — 本轮完成
2. [ ] **v7 DoD #2 启动** — 空数据集/单类数据集/极端值验证
3. [ ] **C4：pytest 超时调查** — 非阻塞，但值得查

---

**版本历史**：
- v28 (2026-06-02 09:50): 早场 — PR#50 merged, v7 DoD #1 完成 ✅
- v27 (2026-06-01 09:45): 早场 — PR#48 创建，ADR-0010 proposed，v7 注册 ✅
