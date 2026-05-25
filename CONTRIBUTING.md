# Contributing to ml-decision-boundary

> **版本**: v1.0.0
> **维护人**: 太子
> **最后更新**: 2026-05-06

---

## 🎯 快速开始

```bash
# 1. Clone
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary

# 2. Install
pip install -r requirements.lock

# 3. Run
python3 main.py

# 4. Test
pytest tests/ -q
```

---

## ✅ 质量门槛（P0/P1/P2）

任何 PR 必须通过以下所有层级：

| 层级 | 命令 | 通过标准 |
|------|------|---------|
| **P0** | `python3 -m py_compile $(find . -name "*.py" -not -path "*/test*" -not -path "*/.pip-packages/*")` | 无错误 |
| **P1** | `python3 -m pytest tests/ -q --tb=short` | 100% pass (216 tests, verified 2026-05-25) |
| **P2** | `python3 -m benchmarks --quick` | Accuracy >= threshold |

> **注意**: 本地验证后再提交，CI 失败会影响所有协作者。

---

## 🔀 分支与 PR 规范

### 分支命名

| 前缀 | 用途 | 示例 |
|------|------|------|
| `fix/` | Bug 修复 | `fix/single-experiment-mode` |
| `feat/` | 新功能 | `feat/new-dataset-support` |
| `docs/` | 文档改进 | `docs/contributing-guide` |
| `ci/` | CI/CD | `ci/github-actions` |
| `daily/` | 每日维护 | `daily/2026-05-06-harness` |

### Commit 规范（Conventional Commits）

```
<type>(<scope>): <short summary>

type: feat | fix | docs | style | refactor | test | chore | ci
scope: cli | api | benchmark | web | deps
```

**示例**：
```bash
git commit -m "feat(cli): add --output option for custom save path"
git commit -m "fix(benchmark): correct accuracy threshold calculation"
git commit -m "docs(readme): add new quick-start example"
```

---

## 📂 项目结构

```
ml-decision-boundary/
├── api/               # 核心 ML API（train_model, compute_decision_boundary 等）
├── benchmarks/        # 基准测试报告和脚本
│   └── reports/       # JSON + Markdown 报告
├── docs/
│   ├── adr/          # 架构决策记录（ADR）
│   ├── DEPENDENCY_POLICY.md  # 依赖治理
│   ├── REPRODUCE.md          # 可复现性指南
│   └── AGENT_CRON_PLAYBOOK.md  # Owner Agent 手册
├── main.py           # CLI 入口（argparse）
├── output/           # 生成的可视化文件（PNG/JSON）
├── spec/             # 核心规范（CHARTER.md, phases.md）
├── strategy/         # Owner Agent 策略文档
│   └── runs/        # 每日执行记录
└── tests/            # pytest 测例
```

---

## 🧪 测试规范

### 测试文件组织

```
tests/
├── conftest.py           # pytest fixtures
├── test_boundary.py      # 决策边界计算
├── test_train.py         # 模型训练
└── test_harness.py      # Benchmark harness
```

### 运行测试

```bash
# 全部测试
pytest tests/ -q

# 带详细输出
pytest tests/ -v

# 只跑单元测试（排除集成）
pytest tests/ -q -m "not integration"
```

### 新增测试要求

| 改动类型 | 要求 |
|---------|------|
| 新增 API 函数 | 必须有对应测试 |
| Bug 修复 | 必须有回归测例 |
| CLI 参数 | 端到端测试（smoke） |

---

## 🎨 代码风格

- **Python**: PEP 8（`black` 格式化）
- **Docstring**: Google style
- **Type hints**: 推荐使用（`-> Type` 注解）
- **错误处理**: 禁止 bare `except:`，禁止 `traceback.format_exc()` 在错误响应中

---

## 📊 Benchmark 规范

### 运行 Benchmark

```bash
# 快速冒烟（1 分钟）
python3 benchmarks/run.py --smoke

# 完整套件（约 3 分钟）
python3 benchmarks/run.py

# 指定数据集+模型
python3 benchmarks/run.py --dataset circles --model SVM
```

### Benchmark 报告

每次完整 benchmark 生成两份报告：
- `benchmarks/reports/YYYY-MM-DD.json` — 机器可读
- `benchmarks/reports/YYYY-MM-DD.md` — 人类可读

报告命名格式：`YYYY-MM-DD-HHMM.md`（精确到分钟）。

---

## 🔄 变更流程

### 提交 PR

```bash
# 1. 从 master 创建分支
git checkout master
git pull origin master
git checkout -b fix/my-bug

# 2. 开发 + 测试
# ...改动...
pytest tests/ -q  # 必须通过

# 3. Commit（Conventional Commits）
git add .
git commit -m "fix(cli): resolve crash when --model is missing"

# 4. Push + PR
git push origin fix/my-bug
# 在 GitHub 上创建 PR
```

### PR 描述模板

```markdown
## 解决的问题
<!-- 简要描述 -->

## 改动范围
<!-- 列出主要文件 -->

## 通过层级
- P0: ✅/❌
- P1: ✅/❌ (N tests)
- P2: ✅/❌ (benchmark result)

## 测试结果
<!-- 粘贴 pytest / benchmark 输出 -->
```

---

## 📌 Owner Agent 说明

本项目由 OpenClaw Owner Agent 管理维护，遵循 `docs/AGENT_CRON_PLAYBOOK.md`。

如需了解项目的维护历史，查看 `strategy/runs/` 目录。

---

**有问题？** 欢迎提 Issue 或 PR！
