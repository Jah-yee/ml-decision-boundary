"""
Hyperparameter sweep configuration for ml-decision-boundary.

Defines per-model hyperparameter grids for systematic tuning experiments.
Each model has a "baseline" config (current defaults) and a "sweep" grid
used by `benchmarks/run.py --hyperparam-sweep`.

Usage:
    from benchmarks.hyperparam_config import SWEEP_GRIDS, BASELINE_CONFIGS
    # SWEEP_GRIDS['SVM'] → list of param dicts to sweep
"""

# ── Baseline configs ────────────────────────────────────────────────────────────
# These mirror the current defaults in benchmarks/run.py MODELS dict.
# Kept as a separate authoritative source to avoid circular imports.

BASELINE_CONFIGS = {
    "SVM":  {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
    "LR":   {"C": 1.0},
    "Tree": {"max_depth": 3},
    "RF":   {"n_estimators": 50, "max_depth": 5},
    "KNN":  {"n_neighbors": 3},
    "MLP":  {"hidden_layer_sizes": (50,), "alpha": 0.001},
    "GB":   {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
    "NB":   {},
    "ET":   {"n_estimators": 100, "max_depth": 10},
    "AB":   {"n_estimators": 50, "learning_rate": 1.0},
}

# ── Sweep grids ────────────────────────────────────────────────────────────────
# Each entry is a list of param dicts to try.
# Results are compared against BASELINE_CONFIGS for regression detection.

SWEEP_GRIDS = {
    "SVM": [
        # kernel=rbf, vary C and gamma
        {"kernel": "rbf", "C": 0.1,  "gamma": "scale"},
        {"kernel": "rbf", "C": 1.0,  "gamma": "scale"},   # baseline
        {"kernel": "rbf", "C": 10.0, "gamma": "scale"},
        {"kernel": "rbf", "C": 100.0,"gamma": "scale"},
        {"kernel": "rbf", "C": 1.0,  "gamma": 0.01},
        {"kernel": "rbf", "C": 1.0,  "gamma": 0.1},
        {"kernel": "rbf", "C": 1.0,  "gamma": 1.0},
        # kernel=linear
        {"kernel": "linear", "C": 0.1},
        {"kernel": "linear", "C": 1.0},
        {"kernel": "linear", "C": 10.0},
    ],
    "LR": [
        {"C": 0.01},
        {"C": 0.1},
        {"C": 1.0},    # baseline
        {"C": 10.0},
        {"C": 100.0},
    ],
    "Tree": [
        {"max_depth": 1},
        {"max_depth": 2},
        {"max_depth": 3},   # baseline
        {"max_depth": 5},
        {"max_depth": 10},
        {"max_depth": None},
    ],
    "RF": [
        {"n_estimators": 10,  "max_depth": 5},
        {"n_estimators": 50,  "max_depth": 5},   # baseline
        {"n_estimators": 100, "max_depth": 5},
        {"n_estimators": 50,  "max_depth": 10},
        {"n_estimators": 50,  "max_depth": None},
        {"n_estimators": 200, "max_depth": 10},
    ],
    "KNN": [
        {"n_neighbors": 1},
        {"n_neighbors": 3},   # baseline
        {"n_neighbors": 5},
        {"n_neighbors": 7},
        {"n_neighbors": 15},
        {"n_neighbors": 31},
    ],
    "MLP": [
        {"hidden_layer_sizes": (50,),           "alpha": 0.0001},
        {"hidden_layer_sizes": (50,),           "alpha": 0.001},   # baseline
        {"hidden_layer_sizes": (50,),           "alpha": 0.01},
        {"hidden_layer_sizes": (100, 50),       "alpha": 0.001},
        {"hidden_layer_sizes": (100, 50),       "alpha": 0.01},
        {"hidden_layer_sizes": (100, 100, 50),  "alpha": 0.001},
    ],
    "GB": [
        {"n_estimators": 50,  "max_depth": 3, "learning_rate": 0.1},  # baseline-ish
        {"n_estimators": 100, "max_depth": 3, "learning_rate": 0.1},
        {"n_estimators": 200, "max_depth": 3, "learning_rate": 0.05},
        {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.1},
        {"n_estimators": 100, "max_depth": 5, "learning_rate": 0.01},
        {"n_estimators": 200, "max_depth": 7, "learning_rate": 0.05},
    ],
    "NB": [
        {},   # No tuneable params for GaussianNB
    ],
    "ET": [
        {"n_estimators": 50,  "max_depth": 10},
        {"n_estimators": 100, "max_depth": 10},  # baseline
        {"n_estimators": 200, "max_depth": 10},
        {"n_estimators": 100, "max_depth": 5},
        {"n_estimators": 100, "max_depth": None},
        {"n_estimators": 200, "max_depth": 20},
    ],
    "AB": [
        {"n_estimators": 25,  "learning_rate": 0.5},
        {"n_estimators": 50,  "learning_rate": 1.0},   # baseline
        {"n_estimators": 100, "learning_rate": 1.0},
        {"n_estimators": 50,  "learning_rate": 0.5},
        {"n_estimators": 100, "learning_rate": 0.5},
    ],
}

# Datasets to run hyperparam sweep on (representative set)
SWEEP_DATASETS = ["circles", "moons", "blobs", "xor"]

# Accuracy regression threshold multiplier vs baseline
# If sweep config is worse than baseline by this fraction, flag as regression
REGRESSION_THRESHOLD = 0.05  # 5% accuracy drop = regression