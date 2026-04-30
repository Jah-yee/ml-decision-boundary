# REPRODUCE.md — ml-decision-boundary

Quick reference for reproducing experiments and benchmarks in this repository.

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

## Core Commands

### Quick smoke test (SVM on circles, ~1s)
```bash
python3 -m benchmarks --quick
```
Expected output: `Accuracy: ~0.79 | Threshold: 0.70 | ✅ PASSED`

### Full benchmark suite (all models × all datasets, ~2-3 min)
```bash
python3 -m benchmarks
```
Expected: 52 experiments, ~45 passed, 7 failed (baseline expected failures on hard configurations).

### Interactive CLI (generates PNG plot)
```bash
python3 main.py
```
Options: `--dataset {circles,moons,blobs,xor}` | `--model {SVM,LR,Tree,RF,KNN,MLP}`

### API server (local)
```bash
python3 -m api.app
# curl http://localhost:5000/api/health
```

---

## Reproducing Specific Results

### Decision boundary visualization for a specific model/dataset
```bash
python3 main.py --dataset circles --model SVM
# Output: output/circles_svm_date.png
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

### Re-run benchmark report (deterministic smoke)
```bash
cd benchmarks/reports
# Edit run.py DATASETS/MODELS to limit scope if needed
python3 -m benchmarks --quick
```

---

## Reproducing Past Benchmark Results

Benchmark outputs are stored in `benchmarks/reports/YYYY-MM-DD.json` and `.md`.

To reproduce results from a specific date:
```bash
# Checkout the commit from that date
git log --oneline --all -- benchmarks/reports/ | head -5

# Or restore a specific report
git show <commit>:benchmarks/reports/2026-04-29.json > /tmp/expected.json
```

---

## Expected Baseline Results

| Dataset | Model | Params | Expected accuracy |
|---------|-------|--------|-------------------|
| circles | SVM | kernel=rbf, C=1 | 0.76–0.80 |
| moons | SVM | kernel=rbf, C=10 | 0.87–0.91 |
| blobs | LR | C=1.0 | ~1.0 |
| xor | MLP | hidden=(100,50) | 0.80–0.85 |

Known expected failures (baseline):
- `circles + SVM + linear kernel` → ~0.43 (expected, non-linear boundary needed)
- `circles + LR + C=1` → ~0.36 (expected)
- `xor + Tree(max_depth=3)` → ~0.46 (expected, insufficient depth)

---

## Troubleshooting

### matplotlib backend error in serverless
```python
import matplotlib
matplotlib.use('Agg')  # Must be before importing pyplot
```

### scikit-learn version mismatch
```bash
pip show scikit-learn | grep Version
# Expected: >= 1.0
```

### Slow MLP training
MLP uses `max_iter=2000`. Reduce for faster iteration:
```python
# In api/train.py or main.py, set max_iter=200 for dev
```

---

## CI/Reproducibility

- **Python**: 3.8–3.11 (tested on 3.10)
- **Random seed**: Fixed at 42 for all model training (reproducible across runs)
- **Dependencies**: `requirements.txt` (no version lock yet — see `spec/DEPENDENCY_POLICY.md`)
- **Coverage**: 89%+ via `pytest --cov=.`

---

*Last verified: 2026-04-30*