# REPRODUCE.md — ml-decision-boundary

Quick reference for reproducing experiments and benchmarks in this repository.

**Last verified**: 2026-05-20 (v4 Reproducibility & Robustness phase)

---

## Environment Setup

```bash
# Clone
git clone https://github.com/Jah-yee/ml-decision-boundary.git
cd ml-decision-boundary

# Install dependencies
pip install -r requirements.txt

# Verify install
python3 -m compileall .
```

---

## Quality Gates (P0 / P1 / P2)

```bash
# P0 — Compileall smoke (must pass before anything else)
python3 -m py_compile $(find . -name "*.py" -not -path "*/test*" -not -path "*/.pip-packages/*" -not -path "*/__pycache__/*")

# P1 — Unit tests
pytest tests/ -q --tb=short
# Expected: 100 passed (verified 2026-05-20)

# P2 — Benchmark smoke (CI gate)
python3 -m benchmarks --quick
# Expected: Accuracy: ~0.79 | Threshold: 0.70 | ✅ PASSED
```

---

## Core Commands

### Quick smoke test (SVM on circles, ~1s)
```bash
python3 -m benchmarks --quick
```
Expected: `Accuracy: 0.7900 | Threshold: 0.7000 | ✅ PASSED`

### Full benchmark suite (all models × all datasets, ~3-5 min)
```bash
python3 -m benchmarks
```
Expected: ~100 experiments, ~89 passed, 11 expected-fail (baseline documented below).

### Tree depth sensitivity sweep (Tree model × 6 depths × 5 datasets)
```bash
python3 -m benchmarks --depth-sweep
```
Expected: 30 experiments, ~27 passed. Reports: `benchmarks/reports/depth_sweep_YYYY-MM-DD.{json,md}`

### Hyperparameter sweep (all models × sweep grids × 4 datasets)
```bash
python3 -m benchmarks --hyperparam-sweep
```
Regression detection: sweep config worse than baseline by >5% → flagged. Reports: `benchmarks/reports/hyperparam_sweep_YYYY-MM-DD.{json,md}`

### Interactive CLI (generates PNG plot)
```bash
python3 main.py
```
Options: `--dataset {circles,moons,blobs,xor,s_curve}` | `--model {SVM,LR,Tree,RF,KNN,MLP,GB,NB,ET,AB}`

### API server (local)
```bash
python3 -m api.app
# curl http://localhost:5000/api/health
```

---

## Platform Architecture

Since v3 (platform cleanup, PR#36), dataset generators and train utilities are consolidated in `core/`:

```python
from core.datasets import DATASET_GENERATORS  # circles, moons, blobs, xor, s_curve
from core.train_utils import build_model      # all 10 model types
```

All three entry points (`main.py`, `api/train.py`, `web/server.py`) share the same implementation via `core/` — eliminating prior duplication of ~380 lines.

---

## Reproducing Specific Results

### Decision boundary visualization for a specific model/dataset
```bash
python3 main.py --dataset circles --model SVM
# Output: output/circles_svm_YYYY-MM-DD.png
```

### Tree depth sensitivity on a single dataset
```bash
# circles + Tree at different depths
for depth in 1 2 3 5 10; do
  python3 main.py --dataset circles --model Tree --params max_depth=$depth
done
```

### Full experiment matrix with custom parameters
```python
from main import run_experiment, run_all_experiments

# Single experiment
result = run_experiment('circles', 'SVM', {'kernel': 'rbf', 'C': 1.0, 'gamma': 'scale'})
print(f"Accuracy: {result.accuracy:.4f}")

# Full matrix
results = run_all_experiments()
```

---

## Expected Baseline Results

### Full benchmark (all models × all datasets)

| Dataset | Model | Params | Expected accuracy | Notes |
|---------|-------|--------|-------------------|-------|
| circles | SVM | kernel=rbf, C=1 | 0.76–0.80 | ✅ Baseline |
| circles | SVM | kernel=rbf, C=10 | 0.78–0.82 | ✅ |
| circles | SVM | kernel=linear, C=1 | 0.36–0.43 | ❌ Expected (non-linear boundary needed) |
| circles | LR | C=1.0 | 0.36–0.40 | ❌ Expected (linear boundary insufficient) |
| circles | Tree | max_depth=3 | 0.68–0.72 | ✅ |
| circles | Tree | max_depth=5 | 0.72–0.76 | ✅ Peak (see Tree depth notes) |
| circles | Tree | max_depth=10 | 0.66–0.70 | ✅ (overfitting begins) |
| circles | Tree | max_depth=None | 0.64–0.68 | ⚠️ Overfits (do not use None) |
| circles | KNN | n_neighbors=3 | 0.64–0.68 | ✅ |
| circles | KNN | n_neighbors=7 | 0.68–0.72 | ✅ |
| circles | KNN | n_neighbors=15 | 0.65–0.69 | ✅ |
| circles | GB | n_est=100, depth=3 | 0.76–0.80 | ✅ |
| circles | ET | n_est=100, depth=10 | 0.76–0.80 | ✅ |
| circles | MLP | hidden=(50,) | 0.75–0.80 | ✅ |
| moons | SVM | kernel=rbf, C=10 | 0.87–0.91 | ✅ Best config |
| moons | Tree | max_depth=5 | 0.88–0.92 | ✅ Peak |
| moons | Tree | max_depth=None | 0.80–0.84 | ⚠️ Overfits |
| moons | MLP | hidden=(100,50) | 0.85–0.90 | ✅ |
| blobs | LR | C=1.0 | ~1.00 | ✅ Linearly separable |
| blobs | Tree | max_depth=2 | ~1.00 | ✅ Saturates at depth=2 |
| blobs | KNN | n_neighbors=3 | ~0.99 | ✅ |
| xor | MLP | hidden=(100,50) | 0.80–0.85 | ✅ Best model for XOR |
| xor | Tree | max_depth=3 | 0.44–0.48 | ❌ Expected (insufficient depth) |
| xor | Tree | max_depth=5 | 0.73–0.77 | ✅ Breakthrough depth |
| xor | Tree | max_depth=None | 0.73–0.77 | ✅ Stable at unlimited |
| xor | SVM | kernel=rbf, C=1 | 0.75–0.80 | ✅ |
| xor | NB | (none) | 0.44–0.48 | ❌ Expected (NB linear assumptions fail on XOR) |
| xor | AB | n_est=50 | 0.48–0.52 | ❌ Expected |
| xor | AB | n_est=100 | 0.50–0.55 | ❌ Expected |
| s_curve | SVM | kernel=rbf, C=1 | 0.55–0.60 | ✅ |
| s_curve | Tree | max_depth=5 | 0.58–0.65 | ✅ |
| s_curve | KNN | n_neighbors=3 | 0.50–0.55 | ✅ |
| s_curve | GB | n_est=100, depth=3 | 0.58–0.65 | ✅ |

**Summary**: ~89/100 pass, 11 expected-fail (documented as design limitations, not regressions).

---

## Tree Depth Notes (Key Finding from 2026-05-01 Research)

Tree model accuracy is **non-monotonic** with `max_depth` on most datasets:

| Dataset | d=1 | d=2 | d=3 | d=5 | d=10 | d=None | Recommended |
|---------|-----|-----|-----|-----|------|--------|-------------|
| circles | 0.60 | 0.65 | 0.70 | **0.74** | 0.68 | 0.66 | **depth=5** (peak) |
| moons | 0.84 | 0.89 | 0.89 | **0.90** | 0.82 | 0.82 | **depth=5** (peak) |
| blobs | 0.60 | **1.00** | 1.00 | 1.00 | 1.00 | 1.00 | **depth=2** (saturates) |
| xor | 0.47 | 0.49 | 0.46 | **0.75** | 0.73 | 0.75 | **depth≥5** (breakthrough) |
| s_curve | 0.66 | 0.66 | 0.56 | **0.63** | 0.57 | 0.57 | **depth=5** |

**Why depth=5 peaks on circles/moons**: Beyond depth=5, the tree overfits — produces too many small leaf nodes that memorize noise, degrading generalization. This is a **counter-intuitive overfitting** pattern.

**Recommendations**:
- For interactive use (`python3 main.py --model Tree`): default behavior uses `max_depth=None` (unlimited) — be aware it may underperform on circles/moons
- For benchmark: Tree configs use depth=3 and depth=10, with depth-specific thresholds calibrated in `DEPTH_TREE_THRESHOLDS`
- For production: prefer depth=5 for circles/moons, depth≥5 for xor, depth=2 for blobs

---

## Reproducing Past Benchmark Results

Benchmark outputs are stored in `benchmarks/reports/YYYY-MM-DD.json` and `.md`.

```bash
# List all benchmark reports
ls -t benchmarks/reports/*.json | head -10

# Restore a specific report
git show <commit>:benchmarks/reports/2026-04-29.json > /tmp/expected.json

# Compare two reports
python3 -c "
import json
a = json.load(open('benchmarks/reports/2026-05-10.json'))
b = json.load(open('benchmarks/reports/2026-05-20.json'))
# Compare pass rates
print(f'May 10: {sum(1 for r in a[\"results\"] if r[\"passed\"])}/{len(a[\"results\"])}')
print(f'May 20: {sum(1 for r in b[\"results\"] if r[\"passed\"])}/{len(b[\"results\"])}')
"
```

---

## Troubleshooting

### matplotlib backend error in serverless
```python
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot
```
All entry points (main.py, api/train.py, web/server.py) already handle this.

### scikit-learn version mismatch
```bash
pip show scikit-learn | grep Version
# Expected: >= 1.0
```

### Slow MLP training
MLP uses `max_iter=2000`. To speed up development:
```python
# In main.py or core/train_utils.py, set max_iter=200 temporarily
```

### pytest hangs
Run with timeout: `timeout 180 pytest tests/ -q --tb=short`

### Import errors after refactoring
Verify core/ module is importable:
```bash
python3 -c "from core.datasets import DATASET_GENERATORS; from core.train_utils import build_model; print('OK')"
```

---

## CI / Reproducibility

- **Python**: 3.8–3.11 (tested on 3.10 in GitHub Actions)
- **Random seed**: Fixed at 42 for all model training (reproducible across runs)
- **Dependencies**: `requirements.lock` (pip-compile generated, committed)
- **Coverage**: 89%+ via `pytest --cov=.`
- **CI Pipeline** (`.github/workflows/ci.yml`):
  - P0: compileall smoke
  - P1: pytest (100 tests)
  - P2: benchmark smoke (`python3 benchmarks/run.py --quick`)
  - Tree depth sweep: runs via `python3 benchmarks/run.py --depth-sweep`
  - Hyperparameter sweep: runs via `python3 benchmarks/run.py --hyperparam-sweep`

---

*Last verified: 2026-05-20*