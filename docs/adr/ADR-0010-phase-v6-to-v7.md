# ADR-0010 — Phase v6 → v7 升级判定

**日期**: 2026-06-01
**状态**: Proposed
**决策者**: 太子

---

## 背景

v6（Stability & Extensibility）阶段已完成全部 DoD 项目（ADR-0009）：

| # | DoD 项目 | 状态 |
|---|---------|------|
| 1 | respx/httpx 本地 env 冲突修复 | ✅ PR#42 merged |
| 2 | core/train_utils.py build_model 重复定义清理 | ✅ PR#42 merged |
| 3 | API contract test 覆盖增强 | ✅ PR#44 merged |
| 4 | Release 自动化（GitHub Release） | ✅ PR#45 merged |
| 5 | 文档 v5/v6 更新至 README/SPEC | ✅ PR#47 merged |

同时 ADR-0009 已 Accepted（2026-05-28）。v6 的所有计划目标均已完成，项目具备进入 v7 的条件。

---

## v6 阶段总结

### 完成项
- pytest 修复（respx env 冲突 → 移除 respx）
- 技术债务清理（train_utils dedup）
- API contract test 增强（15 tests, 400/500 errors）
- GitHub Release 自动化（on `v*` tag）
- README/SPEC.md 同步 v6 phase badge

### 已知技术债务（v7 规划参考）
- **C4**: pytest 完整套件运行超时（非阻塞，本地 sklearn MLP 收敛慢）

---

## v7 方向提案

v7 主题：**Extensibility, Edge Cases & UX**

v6 建立了平台稳定性基线。下一步自然演进方向：
1. **可扩展性**：让用户/贡献者能以插件方式扩展模型和数据集，降低接入门槛
2. **边界处理**：系统性地处理真实使用中的边界情况，提升鲁棒性
3. **用户体验**：改进错误提示、可视化输出质量、日常使用便利性

### v7 候选方向（待进一步细化）

| 方向 | 描述 | 优先级 |
|------|------|--------|
| 自定义模型插件接口 | 用户可注册自己的模型 builder，无需修改核心代码 | P1 |
| 数据集边界验证 | 空数据集、单类数据集、极端值等边界情况优雅处理 | P1 |
| 错误信息改进 | 当模型/数据集/参数异常时给出可操作的提示 | P1 |
| Benchmark 报告增强 | HTML 报告添加更多元信息（运行时环境、参数 hash） | P2 |
| 覆盖率报告自动化 | coverage report 纳入 CI，与 v7 DoD 挂钩 | P2 |
| C4: pytest 超时修复 | 诊断并修复 sklearn MLP 收敛导致的超时 | P3 |

### 判定
- v6 DoD 全部 5 项完成 ✅
- ADR-0009 已 Accepted ✅
- **结论**：满足 v6→v7 升级条件

---

## 决策

**升级 v6 → v7**，进入 Extensibility, Edge Cases & UX 阶段。

v7 DoD 将在下次 Owner cron 中细化并通过单独 ADR（ADR-0011）记录。

---

**版本历史**：
- v1 (2026-06-01): Initial — v6→v7 upgrade decision, Extensibility & Edge Cases theme
