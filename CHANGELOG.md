# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased] — 2026-06-06 Evening (v30 — v7 complete, v8 planning)

### Added
- `core/error_messages.py`: Canonical error code definitions (E1xxx/E2xxx/E3xxx/E4xxx) + format_error() helper — all errors now use standardized codes with hints
- `core/validation.py`: validate_dataset() + validate_model_params() — boundary validation for empty/too-few/single-class datasets, NaN/Inf, and invalid model params
- `tests/test_validation.py`: 33 test cases covering all boundary scenarios
- `main.py`: wire validate_dataset() into generate_dataset() and validate_model_params() into run_experiment()
- `core/plugins/models/svm_plugin.py` — SVM plugin demonstrating ModelBuilder interface
- `core/interfaces.py` — ModelBuilder abstract interface for plugin system
- `core/plugins/registry.py` — Plugin registry with discover_plugins() and get_plugin_model()
- `tests/test_plugins.py` — Plugin system tests (auto-discovery, SVM loading, error handling)
- `docs/adr/ADR-0011-v7-dod.md` — v7 DoD 细化: Extensibility, Edge Cases & UX

### Changed
- `core/validation.py`: All 6 dataset validation + 3 model param validation errors now use canonical error codes (E1001-E1006, E3001-E3003)
- `core/train_utils.py`: build_model() plugin-aware with helpful error messages
- `main.py`: 3 ValueError sites use canonical codes (E3005, E1007) + helpful plugin-aware messages
- `api/train.py`: dataset unknown error uses E1007
- **main.py** — delegate dataset generation to `core/datasets.py`; removed 5 local function copies (`make_circles/moons/blobs/xor/s_curve`), now calls `DATASET_GENERATORS` dispatcher directly; backward compatibility preserved for tests/ and benchmarks/
- **docs/DEPENDENCY_POLICY.md** — Added Section 6: pip-audit integration, known acceptable vulns, local audit guide
- **ADR-0007-v5-dod.md** — Status: Proposed → Accepted (v5 DoD items 1-3 all implemented)

### CI
- **ci.yml** — Added `security-audit` job: pip-audit -r requirements.lock
- **ci.yml** — Added `quality-checks` job: check_readme_consistency.py
- **ci.yml** — Node.js 20 → 24 migration notes (deprecation warnings)

### Fixed
- **benchmarks/run.py** — Regression detection: only compare baseline configs (exact param match); non-baseline sweep configs are excluded from regression checks (fixes 45 false-positive regressions)
- **core/train_utils.py** — Remove duplicate build_model definition; consolidate lazy + direct factories into direct imports at module top; shrinks file by ~50 lines (ADR-0009 v6 DoD)
- **web/server.py** — Security fix: remove traceback.format_exc() from /train error handler to prevent internal path/dependency exposure (#35)

### Governance (v30 Evening)
- **docs/adr/ADR-0012-phase-v7-to-v8.md** — New ADR: v7→v8 upgrade decision, Model Registry & Lifecycle theme (Proposed)
- **spec/phases.md** — v7 marked complete, v8 entry conditions defined
- **strategy/NEXT_ROUND_THEME.md** — v30: v7 完成，v8 规划启动

## [0.1.1] — 2026-05-01

### Added
- **spec/phases.md** — v3 completed, v4 started; ADR-0005 phase upgrade created
- **docs/adr/ADR-0004-v3-platformization.md** — status updated to Accepted (PR#36 merged)
- **docs/adr/ADR-0005-phase-v3-to-v4.md** — new ADR: v3→v4 upgrade decision
- **core/datasets.py** — make_blobs normalized to 2-class (blobs fix, commit 5678e4f)
- **core/datasets.py** — Shared dataset generators (make_circles/make_moons/make_blobs/make_xor/make_s_curve); consolidated from api/train.py + web/server.py
- **core/train_utils.py** — Shared ML utilities (build_model/slider_to_params/compute_boundary_grid/get_model_info_dict); consolidated from api/train.py + web/server.py
- **api/train.py** — Refactored to import from core/; removed ~160 lines of duplication; removed unused matplotlib import
- **web/server.py** — Refactored to import from core/; removed ~220 lines of duplication; all three entry points now consistent
- **benchmarks/run.py** — Fix: stored_baseline (from JSON) vs inline_baseline (live) — prevents live-best-vs-itself regression comparison; exit code 1 on regressions > 0
- **tests/test_boundary_cases.py** — 116 new tests: noise extremes, seed stability, unexplored dataset×model combos, model edge params, small-sample boundary, high-noise stress test
- **benchmarks/hyperparam_config.py** — Hyperparameter sweep configuration: SWEEP_GRIDS (per-model param grids), BASELINE_CONFIGS (baseline defaults), SWEEP_DATASETS, REGRESSION_THRESHOLD (5%% accuracy drop = regression)
- **benchmarks/run.py** — `run_hyperparam_sweep()`: systematic hyperparameter tuning across all models × SWEEP_DATASETS, compares against baselines, detects regressions; `write_hyperparam_report()` outputs JSON+MD reports; CLI: `--hyperparam-sweep`
- **benchmarks/run.py** — s_curve integration: ACCURACY_THRESHOLDS (0.55), DEPTH_TREE_THRESHOLDS (calibrated per depth), added to DATASETS list and `generate_summary()` by_dataset stats
- **main.py** — `run_all_experiments()` includes s_curve dataset in the full experiment suite
- **docs/adr/ADR-0003-phase-v2-to-v3.md** — Phase v2→v3 升级判定: v2 DoD 全部完成（SPEC.md拆分, CLI改进, GitHub Actions CI, CONTRIBUTING.md完善, benchmark报告HTML化）; v3 进入 Platform 阶段 (PR#22)
- **benchmarks/report_html.py** — HTML 报告生成器（372行）：支持 accuracy_trend / train_time_trend / summary_trend 三种趋势图，matplotlib dark-theme，自动加载 benchmarks/reports/ 下所有 JSON
- **benchmarks/run.py** — 新增 `--html` flag：benchmark 结束后自动调用 report_html 生成 HTML + PNG charts
- **benchmarks/reports/2026-05-07.{html,json,md,*_trend.png}** — 2026-05-07 晚间 session HTML 报告（此前未 commit）
- **benchmarks/reports/2026-05-08.{html,json,md,*_trend.png}** — 2026-05-08 晨间 session HTML 报告
- **main.py** — CLI rewrite: add argparse with --help, --quick (smoke test), --list-models, --list-datasets; structured help epilog with examples (PR#20)
- **CONTRIBUTING.md** — New contributor guide: quick start, P0/P1/P2 quality gates, branch/PR workflow, coding style, Conventional Commits format (PR#20)
- **main.py (2026-05-05)** — CLI enhancement: add argparse with `--model`, `--dataset`, `--params KEY=VALUE`, `--output`, `--n-samples`, `--noise`, `--seed`, `--resolution`, `--verbose`, `--list-models`; single-experiment mode via `--model SVM --dataset circles`
- **main.py (2026-05-05 evening)** — Fix CLI single-experiment crash: remove stale `compute_decision_boundary(result, ...)` call where result is ModelResult (not a model); keep only `compute_decision_boundary(trained_model, X)` path
- **benchmarks/run.py (2026-05-05)** — CLI help improvement: add `prog=` name, epilog examples, run_depth_sweep docstring added
- **docs/adr/ADR-0002-phase-v1-to-v2.md** — Phase v1→v2 升级判定: v1 DoD 全部完成（pytest 89%, API全覆盖, benchmark标准化, 安全修复, REPRODUCE.md）; v2 进入 Model & Data Expansion 阶段 (PR#18)