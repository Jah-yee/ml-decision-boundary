# ADR-0007 — v5 DoD 细化：Automation & Documentation

**日期**: 2026-05-25
**状态**: Accepted
**决策者**: 太子

---

## 背景

v5 阶段（Automation & Documentation）已于 2026-05-25 正式通过 ADR-0006 启动。

v5 的核心目标是提升项目的自动化运维能力和文档质量，减少手动维护负担，同时确保文档与实现保持同步。

---

## v5 DoD 候选项目

基于 v4 完成后的扫描结果和 playbook 的 5 分叉分析，提出以下 v5 DoD 项目：

### 候选 1：CHANGELOG 自动化生成
**问题**：CHANGELOG.md 靠手动维护，容易遗漏、更新不及时。

**解决方案**：实现基于 Conventional Commits 的自动 CHANGELOG 生成脚本。

**预期交付**：
- `scripts/generate_changelog.py` — 从 git log 提取 conventional commits 生成 CHANGELOG 条目
- GitHub Actions hook 在 PR merge 时自动更新 CHANGELOG
- 或：将 CHANGELOG 生成集成到 release 流程

**验证标准**：
- 运行 `python3 scripts/generate_changelog.py` 输出的格式与现有 CHANGELOG.md 格式一致
- 不遗漏已 conventionalize 的 commit

**时间估算**：~1-2 hours

---

### 候选 2：依赖安全审核自动化
**问题**：当前没有依赖漏洞检测机制，DEPENDENCY_POLICY.md 的 D1-D5 靠人工审核。

**解决方案**：集成 pip-audit 到 CI pipeline。

**预期交付**：
- `pip install pip-audit` 并在 CI 中运行 `pip-audit`
- 添加 `ci.yml` job：security-audit，运行 pip-audit，失败则阻止 merge
- 更新 DEPENDENCY_POLICY.md 反映这一变更

**验证标准**：
- pip-audit 无漏洞输出（或已知的可接受漏洞已记录）
- CI security-audit job 通过

**时间估算**：~1-2 hours

---

### 候选 3：README/SPEC.md 与代码实现一致性检查
**问题**：README 或 SPEC.md 中的命令、参数列表可能与实际代码不同步。

**解决方案**：添加文档一致性 CI 检查。

**预期交付**：
- `scripts/check_readme_consistency.py` — 验证 README 中的命令在代码中存在
- 或：添加 README 中引用的所有 CLI 参数的端到端覆盖测试
- 集成到 ci.yml quality-gates job

**验证标准**：
- README 中的 `--model` 和 `--dataset` 参数列表与 `main.py` argparse 定义一致
- README 中引用的所有 API endpoint 在 `web/server.py` 或 `api/train.py` 中存在

**时间估算**：~1-2 hours

---

### 候选 4：GitHub Release 自动化
**问题**：手动创建 release 需要大量人工操作。

**解决方案**：基于 semantic tag 自动发布。

**预期交付**：
- `scripts/bump_version.py` — 语义化版本号递增脚本
- GitHub Actions workflow：`release.yml`，在 push tag 时自动：
  - 构建 sdist/wheel
  - 生成 GitHub Release notes（从 CHANGELOG）
  - 上传到 GitHub Release

**验证标准**：
- `git tag v0.1.0 && git push origin v0.1.0` 触发完整 release workflow
- GitHub Release 包含生成的 release notes 和预构建包

**时间估算**：~2-3 hours（涉及 CI 配置和 GitHub API）

---

## 决策

### 提议的 v5 DoD（3 项）

| # | DoD 项目 | 验证标准 |
|---|---------|---------|
| 1 | CHANGELOG 自动化生成 | `scripts/generate_changelog.py` 成功运行并输出格式正确的 CHANGELOG 条目 |
| 2 | 依赖安全审核 CI | `pip-audit` 集成到 CI，security-audit job 通过，DEPENDENCY_POLICY.md 更新 |
| 3 | README/SPEC.md 一致性 CI | `scripts/check_readme_consistency.py` 集成到 CI quality-gates，检测任何不一致 |

**排除项目**：
- GitHub Release 自动化 — 推迟到 v5 后期（需要更多时间和 GitHub API 配置经验）
- 自动发行（版本号管理）— 依赖 Release 自动化，先不做

---

## 下一步

1. 本轮 cron（2026-05-25 PM）实现 DoD 项目 1（CHANGELOG 自动化）
2. 后续 cron 实现 DoD 项目 2（依赖安全审核）
3. 再后续 cron 实现 DoD 项目 3（README 一致性检查）

---

**版本历史**：
- v1 (2026-05-25): 初稿