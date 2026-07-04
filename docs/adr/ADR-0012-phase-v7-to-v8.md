# ADR-0012 — Phase v7 → v8 升级判定

**日期**: 2026-06-06
**状态**: Proposed
**决策者**: 太子

---

## 背景

v7（Extensibility, Edge Cases & UX）阶段已完成全部 DoD 项目（ADR-0011）：

| # | DoD 项目 | 状态 |
|---|---------|------|
| 1 | 自定义模型插件接口 | ✅ PR#50 merged |
| 2 | 数据集边界验证 | ✅ PR#51 merged |
| 3 | 错误信息改进 | ✅ PR#52 merged |
| 4 | C4: pytest 超时修复 | ✅ PR#53 merged |
| 5 | ADR-0011 Accepted 后同步 | ✅ v29 早场完成 |

ADR-0011 已于 2026-06-06 更新为 Accepted 状态。v7 的所有计划目标均已完成，项目具备进入 v8 的条件。

---

## v7 阶段总结

### 完成项
- 自定义模型插件接口（`core/plugins/models/` 动态加载）
- 数据集边界验证（空数据集、单类、极端值优雅处理）
- 错误信息标准化（canonical error codes + 行动建议）
- C4 pytest 超时修复（重复测试跳过，套件 2min 内完成）
- ADR-0011 → Accepted

### 已知技术债务（v8 规划参考）
- **C5**: 模型训练结果无持久化 → 每次运行独立，无版本追踪
- **C6**: benchmark 输出无结构化 registry → 回归检测依赖手动
- **C7**: 插件接口无版本声明机制 → 接口演化无约束

---

## v8 方向提案

v8 主题：**Model Registry & Lifecycle（模型注册与生命周期管理）**

v7 建立了插件接口，下一步自然演进：让训练出的模型可追踪、可复用、可回滚。

### v8 候选方向

| 方向 | 描述 | 优先级 |
|------|------|--------|
| **模型注册表（Model Registry）** | 训练结果持久化到 `~/.ml-decision-boundary/registry/`；每次训练自动记录元数据（模型类型、超参数、数据集 hash、训练时间、精度） | P1 |
| **模型序列化 & 加载** | 支持 `save_model()` / `load_model()` 接口；插件模型同样适用 | P1 |
| **CLI 模型管理命令** | `ml-db model list` / `ml-db model inspect <id>` / `ml-db model delete <id>` | P1 |
| **Benchmark Registry** | benchmark 结果写入 registry，支持回归趋势查询 | P2 |
| **插件版本声明** | 插件文件声明 `version = "0.1.0"` 和 `api_version`，接口演化有约束 | P2 |

### v8 候选 DoD（待进一步细化）

| # | DoD 项目 | 描述 | 优先级 |
|---|---------|------|--------|
| 1 | Model Registry 核心 | 训练结果自动注册，元数据 JSON 持久化 | P1 |
| 2 | 模型序列化 | `save`/`load` 接口，支持插件模型 | P1 |
| 3 | CLI 模型管理 | `list`/`inspect`/`delete` 命令 | P1 |
| 4 | ADR-0012 Accepted 后同步 | NEXT_ROUND_THEME 更新 | P0 |

### 判定
- v7 DoD 全部 5 项完成 ✅
- ADR-0011 已 Accepted ✅
- **结论**：满足 v7→v8 升级条件

---

## 决策

**升级 v7 → v8**，进入 Model Registry & Lifecycle 阶段。

v8 DoD 将在下次 Owner cron 中细化并通过单独 ADR（ADR-0013）记录。

---

**版本历史**：
- v1 (2026-06-06): Initial — v7→v8 upgrade decision, Model Registry & Lifecycle theme
