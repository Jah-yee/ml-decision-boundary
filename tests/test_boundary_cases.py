"""
tests/test_boundary_cases.py — Platformization boundary case coverage

Covers:
  1. Noise extremes (0.0, 0.5) across all datasets
  2. Seed-stability: same config run 3×, accuracy within tolerance
  3. Unexplored dataset × model combinations (ET+blobs, AB+xor, etc.)
  4. Model edge params (KNN k=1, SVM linear, LR high-C)
"""

import pytest
import numpy as np
from main import generate_dataset, train_model, run_experiment, ModelResult


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

ALL_DATASETS = ["circles", "moons", "blobs", "xor", "s_curve"]
ALL_SEEDS    = [0, 42, 2026]
ALL_NOISE    = [0.0, 0.5]          # extremes


@pytest.fixture(params=ALL_DATASETS)
def dataset_name(request):
    return request.param


# ─────────────────────────────────────────────────────────────────────────────
# 1. Noise extremes
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dataset", ALL_DATASETS)
@pytest.mark.parametrize("noise", [0.0, 0.5])
def test_noise_extremes_no_crash(dataset, noise):
    """noise=0.0 and noise=0.5 must not raise, and must return valid shapes."""
    X, y = generate_dataset(dataset, n_samples=100, noise=noise, seed=42)
    assert X.shape == (100, 2)
    assert y.shape == (100,)
    assert set(np.unique(y)) <= {0, 1}


@pytest.mark.parametrize("dataset", ALL_DATASETS)
@pytest.mark.parametrize("noise", [0.0, 0.5])
def test_noise_extremes_trainable(dataset, noise):
    """Datasets at noise extremes must be trainable on all model types."""
    X, y = generate_dataset(dataset, n_samples=150, noise=noise, seed=42)
    for model_type, params in [
        ("SVM",  {"C": 1.0, "kernel": "rbf"}),
        ("Tree", {"max_depth": 5}),
        ("KNN",  {"n_neighbors": 5}),
        ("LR",   {"C": 1.0}),
        ("NB",   {}),
    ]:
        model, train_time = train_model(model_type, params, X, y)
        assert train_time >= 0
        acc = model.score(X, y)
        assert 0.0 <= acc <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 2. Seed stability
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dataset", ["circles", "moons", "blobs", "xor"])
@pytest.mark.parametrize("seed", [0, 42, 2026])
def test_seed_stability_same_dataset(dataset, seed):
    """Same dataset+seed must produce identical arrays."""
    X1, y1 = generate_dataset(dataset, n_samples=200, noise=0.3, seed=seed)
    X2, y2 = generate_dataset(dataset, n_samples=200, noise=0.3, seed=seed)
    np.testing.assert_array_almost_equal(X1, X2)
    np.testing.assert_array_equal(y1, y2)


@pytest.mark.parametrize("dataset", ["circles", "moons", "blobs", "xor"])
@pytest.mark.parametrize("seed", [0, 42, 2026])
def test_seed_stability_experiment_accuracy(dataset, seed):
    """run_experiment with same seed must give identical accuracy across runs."""
    params = {"C": 1.0, "kernel": "rbf"}
    r1 = run_experiment(dataset, "SVM", params, seed=seed)
    r2 = run_experiment(dataset, "SVM", params, seed=seed)
    assert abs(r1.accuracy - r2.accuracy) < 1e-6


@pytest.mark.parametrize("seed", [0, 42, 2026])
def test_seed_stability_multiple_models(seed):
    """Different models should all be deterministic under same seed."""
    X, y = generate_dataset("circles", n_samples=200, noise=0.3, seed=seed)
    models = [
        ("SVM",  {"C": 1.0, "kernel": "rbf"}),
        ("Tree", {"max_depth": 5}),
        ("LR",   {"C": 1.0}),
    ]
    for model_type, params in models:
        m1, _ = train_model(model_type, params, X, y)
        m2, _ = train_model(model_type, params, X, y)
        np.testing.assert_array_almost_equal(m1.predict(X), m2.predict(X))


# ─────────────────────────────────────────────────────────────────────────────
# 3. Unexplored dataset × model combinations
# ─────────────────────────────────────────────────────────────────────────────

UNEXPLORED = [
    # (dataset, model, params)
    ("blobs",   "ET",  {"n_estimators": 50, "max_depth": 10}),
    ("blobs",   "AB",  {"n_estimators": 50, "learning_rate": 1.0}),
    ("blobs",   "GB",  {"n_estimators": 50, "max_depth": 3}),
    ("blobs",   "MLP", {"hidden_layer_sizes": (50,), "alpha": 0.001}),
    ("blobs",   "RF",  {"n_estimators": 50, "max_depth": 5}),
    ("xor",     "ET",  {"n_estimators": 50, "max_depth": 10}),
    ("xor",     "AB",  {"n_estimators": 50, "learning_rate": 1.0}),
    ("xor",     "GB",  {"n_estimators": 50, "max_depth": 3}),
    ("xor",     "MLP", {"hidden_layer_sizes": (50,), "alpha": 0.001}),
    ("s_curve", "SVM", {"C": 1.0, "kernel": "rbf"}),
    ("s_curve", "Tree", {"max_depth": 5}),
    ("s_curve", "ET",  {"n_estimators": 50, "max_depth": 10}),
    ("s_curve", "AB",  {"n_estimators": 50, "learning_rate": 1.0}),
    ("s_curve", "GB",  {"n_estimators": 50, "max_depth": 3}),
    ("s_curve", "MLP", {"hidden_layer_sizes": (50,), "alpha": 0.001}),
    ("moons",   "ET",  {"n_estimators": 50, "max_depth": 10}),
    ("moons",   "AB",  {"n_estimators": 50, "learning_rate": 1.0}),
    ("moons",   "GB",  {"n_estimators": 50, "max_depth": 3}),
    ("moons",   "MLP", {"hidden_layer_sizes": (50,), "alpha": 0.001}),
    ("circles", "ET",  {"n_estimators": 50, "max_depth": 10}),
    ("circles", "AB",  {"n_estimators": 50, "learning_rate": 1.0}),
    ("circles", "GB",  {"n_estimators": 50, "max_depth": 3}),
    ("circles", "MLP", {"hidden_layer_sizes": (50,), "alpha": 0.001}),
]


@pytest.mark.parametrize("dataset,model_type,params", UNEXPLORED)
def test_unexplored_combinations(dataset, model_type, params):
    """Unexplored dataset×model combos must train without error."""
    X, y = generate_dataset(dataset, n_samples=200, noise=0.3, seed=42)
    model, train_time = train_model(model_type, params, X, y)
    assert train_time >= 0
    acc = model.score(X, y)
    assert 0.0 <= acc <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 4. Model edge parameters
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("k", [1, 3, 50])
def test_knn_edge_k(k):
    """KNN with k=1, k=3, k=50 should all work on circles."""
    X, y = generate_dataset("circles", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("KNN", {"n_neighbors": k}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


@pytest.mark.parametrize("C", [0.001, 1.0, 100.0])
def test_svm_linear_edge_C(C):
    """SVM linear kernel with extreme C values."""
    X, y = generate_dataset("circles", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("SVM", {"kernel": "linear", "C": C}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


@pytest.mark.parametrize("C", [0.001, 1.0, 1000.0])
def test_lr_edge_C(C):
    """Logistic Regression with extreme C (regularization strength)."""
    X, y = generate_dataset("moons", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("LR", {"C": C}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


@pytest.mark.parametrize("depth", [1, 5, None])
def test_tree_edge_depth(depth):
    """Decision Tree with depth=1, depth=5, depth=None (unlimited)."""
    X, y = generate_dataset("xor", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("Tree", {"max_depth": depth}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


@pytest.mark.parametrize("n_est", [1, 10, 200])
def test_rf_edge_n_estimators(n_est):
    """Random Forest with 1, 10, 200 trees."""
    X, y = generate_dataset("blobs", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("RF", {"n_estimators": n_est, "max_depth": 5}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


@pytest.mark.parametrize("lr", [0.01, 0.5, 2.0])
def test_ab_edge_learning_rate(lr):
    """AdaBoost with extreme learning rates."""
    X, y = generate_dataset("xor", n_samples=200, noise=0.3, seed=42)
    model, _ = train_model("AB", {"n_estimators": 50, "learning_rate": lr}, X, y)
    assert 0.0 <= model.score(X, y) <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 5. run_experiment boundary — ModelResult fields
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dataset,model_type,params", [
    ("circles", "SVM",  {"C": 1.0, "kernel": "rbf"}),
    ("xor",     "Tree", {"max_depth": 5}),
    ("blobs",   "ET",   {"n_estimators": 50, "max_depth": 10}),
    ("moons",   "AB",   {"n_estimators": 50, "learning_rate": 1.0}),
])
def test_run_experiment_returns_complete_result(dataset, model_type, params):
    """run_experiment must return a ModelResult with all expected fields."""
    result = run_experiment(dataset, model_type, params, seed=42)
    assert isinstance(result, ModelResult)
    assert result.name
    assert isinstance(result.params, dict)
    assert 0.0 <= result.accuracy <= 1.0
    assert result.train_time >= 0
    # boundary_points should be a list (may be empty)
    assert isinstance(result.boundary_points, list)


# ─────────────────────────────────────────────────────────────────────────────
# 6. Small-sample boundary
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dataset", ALL_DATASETS)
@pytest.mark.parametrize("n_samples", [10, 2])
def test_small_sample_boundary(dataset, n_samples):
    """Very small n_samples should still produce valid output (2 is min for KNN)."""
    X, y = generate_dataset(dataset, n_samples=n_samples, noise=0.3, seed=42)
    assert X.shape == (n_samples, 2)
    assert y.shape == (n_samples,)
    assert set(np.unique(y)) <= {0, 1}


# ─────────────────────────────────────────────────────────────────────────────
# 7. All datasets with noise=0.5 + seed sweep (stress test)
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("dataset", ["circles", "moons", "blobs", "xor"])
@pytest.mark.parametrize("seed", [0, 42, 2026])
def test_high_noise_seed_sweep(dataset, seed):
    """noise=0.5 with multiple seeds — all must be trainable."""
    X, y = generate_dataset(dataset, n_samples=200, noise=0.5, seed=seed)
    model, t = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)
    assert t >= 0
    assert 0.0 <= model.score(X, y) <= 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 8. Cross-noise consistency check
# ─────────────────────────────────────────────────────────────────────────────

def test_noise_0_does_not_change_class_labels():
    """noise=0 on xor must preserve the perfect XOR structure."""
    X, y = generate_dataset("xor", n_samples=500, noise=0.0, seed=42)
    # With noise=0, the XOR labels should be perfectly separable
    model, _ = train_model("Tree", {"max_depth": None}, X, y)
    acc = model.score(X, y)
    assert acc == 1.0, "Perfect XOR with noise=0 should be perfectly learned"


def test_blobs_noise_ignored():
    """blobs ignores the noise parameter — verify it still runs."""
    for noise in [0.0, 0.3, 0.5]:
        X, y = generate_dataset("blobs", n_samples=200, noise=noise, seed=42)
        model, _ = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)
        assert 0.0 <= model.score(X, y) <= 1.0