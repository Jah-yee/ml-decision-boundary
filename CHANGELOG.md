# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **tests/test_experiment_flow.py** — 15 new tests: run_experiment (10 cases covering all models/datasets) + save_results (5 cases including edge case for empty list)
- **tests/test_benchmarks_smoke.py** — 8 new tests: benchmark CLI smoke + run module integration tests
- **research/2026-04-28-negative-tree-on-xor.md** — Negative result: Tree(depth=3) on XOR achieves only 0.46 accuracy (expected ~0.50); 3 actionable recommendations for benchmark threshold granularity and depth sensitivity testing

### Changed
- **main.py** — save_results([]) edge case fixed: now returns NaN for best_accuracy/fastest_train_time instead of ValueError on empty list

### Metrics
- main.py coverage: **27% → 42%** (+15pp)
- TOTAL coverage: **42% → 60%** (+18pp)
- Tests: **28 → 58** (+30 passing tests)
- benchmark: 52 exp, 45 passed, 7 expected-fail (documented as design limitations, not regressions)

### Added
- **benchmarks/ package** — Standardized benchmark harness with `python3 -m benchmarks` entrypoint (--quick smoke test + full suite), structured JSON + MD report output to benchmarks/reports/
- **ADR-0001** — Phase v0→v1 升级判定文档（正式记录 v0 完成，v1 开始）
- **docs/adr/ADR-0001-phase-v0-to-v1.md** — 阶段升级决策记录
- **spec/phases.md** (v0.2) — 更新：v0 已完成标记，v1 DoD 新增（pytest≥80%, API全覆, benchmark标准化）
- **tests/test_api_contract.py** — 7 new tests for API serverless functions (api/health.py, api/train.py), covering contract consistency and train_model signature cross-module verification
- **benchmarks/reports/2026-04-26.md** — First benchmark report documenting 72-experiment run
- **spec/DEPENDENCY_POLICY.md** (v0.1) — Dependency management policy: principles, environment constraints (serverless/CPU), P0/P1分级, 变更流程
- **benchmarks/reports/2026-04-27.md** — Second benchmark report (72-experiment run, MLP best on circles/xor, blobs linear separable)
- **tests/test_main.py** — +10 new tests: LR/NB model training, dataset edge cases, ModelResult dataclass, API contract signature checks

### Changed
- **requirements.txt** — Added `pytest>=7.0.0` (上轮遗留：pytest 未写入依赖)
- **main.py** — MLP max_iter increased from 500 to 2000 to eliminate ConvergenceWarning (eliminates P1 warning)
- **strategy/NEXT_ROUND_THEME.md** — Updated to mark Harness v1 as next priority

### Fixed
- **main.py** — MLP ConvergenceWarning eliminated (max_iter 500→2000)

### Security
- **api/health.py** — Added contract test to verify health response structure

---

## [0.0.1] — 2026-04-26

### Added
- **spec/CHARTER.md** — Project vision, mission, non-goals, quality bar
- **spec/phases.md** — Phase definitions (v0 Foundation → v1 Testing & Harness → v2 Model Expansion → v3 Platform)
- **spec/REPRODUCE.md** — Reproducibility guide with P0-P3 verification commands
- **tests/** — Test infrastructure with 11 test cases covering datasets and model training

---

## [0.0.0] — 2026-04-25

### Added
- Initial release: ML Decision Boundary Visualizer
- 6 models: SVM, Logistic Regression, Decision Tree, Random Forest, KNN, MLP
- 4 datasets: circles, moons, blobs, xor
- CLI (`python main.py`) and Web interface (`web/server.py`)
- Vercel deployment config
