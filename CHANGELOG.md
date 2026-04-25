# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **spec/CHARTER.md** — Project vision, mission, non-goals, quality bar
- **spec/phases.md** — Phase definitions (v0 Foundation → v1 Testing & Harness → v2 Model Expansion → v3 Platform)
- **spec/REPRODUCE.md** — Reproducibility guide with P0-P3 verification commands
- **tests/** — Test infrastructure with 11 test cases covering datasets and model training
- **benchmarks/reports/2026-04-26.md** — First benchmark report documenting 72-experiment run

### Changed
- **strategy/NEXT_ROUND_THEME.md** — Updated to mark Harness v1 as next priority

### Fixed
- Documentation of `train_model()` API signature corrected (actual: model_type, params, X, y)

---

## [0.0.0] — 2026-04-25

### Added
- Initial release: ML Decision Boundary Visualizer
- 6 models: SVM, Logistic Regression, Decision Tree, Random Forest, KNN, MLP
- 4 datasets: circles, moons, blobs, xor
- CLI (`python main.py`) and Web interface (`web/server.py`)
- Vercel deployment config
