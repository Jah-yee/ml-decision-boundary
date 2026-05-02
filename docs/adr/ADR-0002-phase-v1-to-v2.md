# ADR-0002 — Phase v1 → v2 升级判定

**日期**: 2026-05-02
**状态**: Accepted
**决策者**: ml-decision-boundary cron agent (taizi)

---

## 背景

v1 Testing & Harness 阶段的 DoD 条目在 2026-05-02 已全部完成。本 ADR 记录正式的阶段升级判定，并为 v2 阶段建立基线。

v1 阶段引入了 Tree depth sensitivity sweep、pip-lock 依赖锁、API 错误响应格式统一、REPRODUCE.md 等关键交付物，同时保持了高质量的测试覆盖（89%）和安全实践（traceback 移除）。

---

## v1 阶段 DoD 实际完成情况

| DoD 条目 | 状态 | 证据 |
|---------|------|------|
| pytest 覆盖率 ≥ 80%（main.py 核心路径） | ✅ 完成 | 当前 89% 覆盖率 |
| API 端点全测试覆盖 | ✅ 完成 | 19 个 API 测例（test_api_contract.py 7个 + test_main.py 12个） |
| benchmark 命令标准化为 `python3 -m benchmark` | ✅ 完成 | benchmarks/run.py 可通过 `python3 -m benchmarks.run` 执行 |
| 安全修复（traceback.format_exc() 移除） | ✅ 完成 | PR#14 commit 50b61c8 |
| REPRODUCE.md 新建 | ✅ 完成 | spec/REPRODUCE.md 存在，含快速开始、基线结果、故障排查 |

### v1 附加交付物（超出 DoD）

| 交付物 | 描述 |
|--------|------|
| DEPENDENCY_POLICY.md | 依赖管理政策，含 pip-lock/pip-compile 流程 |
| requirements.lock | pip-compile 生成的锁定依赖文件 |
| Tree depth sensitivity sweep | `--depth-sweep` flag，6个 depth × 4个 dataset = 24 实验 |
| API 错误响应格式统一 | `code` 字段 + sanitize 500 errors (commit d03df11) |
| research/2026-05-01-tree-depth-sensitivity.md | Tree depth 失败模式研究文档 |
| benchmarks/reports/ HTML + JSON | 标准化 benchmark 报告输出 |

---

## v2 阶段定义：Model & Data Expansion

**目标**: 扩展模型族和数据集，建立科学评估体系

### v2 入口条件（从 v1 继承）
- P0 ✅ (python3 -m compileall . 无错误)
- P1 ✅ (pytest 89% 覆盖率，API 全覆盖)
- P2 ✅ (benchmarks/reports 可重复产出)
- DEPENDENCY_POLICY.md ✅ (pip-lock 流程就绪)

### v2 阶段 DoD（待本轮 cron 执行后填充）

```
- [ ] SPEC.md 拆分（从 spec/ 目录移除混杂文件）
- [ ] CLI 帮助文本改进
- [ ] ADR-0002 本 ADR 创建 ← 本轮交付
```

---

## 升级判定

**v1 → v2 阶段升级条件已满足。**

判定依据：
- v1 DoD 全部 5 项 ✅
- v1 附加交付物（Tree depth sweep、pip-lock、API 统一）✅
- phases.md 当前阶段仍标注 "v1 进行中"，需更新

---

## 决策

v1 阶段正式结束，当前阶段更新为 v2 — Model & Data Expansion。
phases.md 将同步更新。

---

## 下一步

1. 更新 `spec/phases.md`：将"当前阶段: v1 — Testing & Harness"改为"当前阶段: v2 — Model & Data Expansion"
2. 清理 phases.md 中 v1 的已完成 DoD 标记
3. 向 CHANGELOG.md Unreleased 添加 v1→v2 升级条目
4. 下一轮 cron 可继续 v2 DoD：SPEC.md 拆分、CLI 改进等

---

## 参考

- ADR-0001: Phase v0 → v1 升级判定（2026-04-27）
- benchmarks/reports/depth_sweep_2026-05-01.md — Tree depth sensitivity findings
- research/2026-05-01-tree-depth-sensitivity.md — 实验细节