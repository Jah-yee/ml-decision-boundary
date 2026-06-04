"""
core/error_messages.py — Standardized error message definitions

Every error raised in this project uses one of these canonical messages.
This ensures consistency across CLI, API, and library consumers.

Error code format: E{category}{number}
- 1xxx: Dataset errors
- 2xxx: Model errors
- 3xxx: Parameter errors
- 4xxx: System errors
"""

from typing import Optional


# ── Dataset Errors (1xxx) ────────────────────────────────────────────────────────

E1001_EMPTY = (
    "[E1001] Dataset is empty. "
    "Need at least 2 samples for classification. "
    "Hint: python main.py --n-samples 500"
)

E1002_TOO_FEW = (
    "[E1002] Dataset has only {n} sample(s). "
    "Need at least 2 samples for classification. "
    "Hint: python main.py --n-samples 500"
)

E1003_LENGTH_MISMATCH = (
    "[E1003] X and y have mismatched lengths: "
    "X has {n_x} samples, but len(y)={n_y}. "
    "Ensure X and y have the same number of rows."
)

E1004_SINGLE_CLASS = (
    "[E1004] Only 1 class found in labels for '{dataset}': {labels}. "
    "Need at least 2 classes for classification. "
    "Hint: Check your dataset or try a different seed."
)

E1005_ALL_NAN_INF = (
    "[E1005] Dataset contains only NaN or Inf values. "
    "Please check your data source."
)

E1006_NO_VALID_VALUES = (
    "[E1006] Dataset has no valid (finite) numeric values. "
    "All feature values are NaN or Inf."
)

E1007_UNKNOWN_DATASET = (
    "[E1007] Unknown dataset: '{name}'. "
    "Available: circles, moons, blobs, xor, s_curve. "
    "Hint: python main.py --list-models"
)


# ── Model Errors (2xxx) ─────────────────────────────────────────────────────────

E2001_UNKNOWN_MODEL = (
    "[E2001] Unknown model: '{name}'. "
    "Available: SVM, LR, Tree, RF, KNN, MLP, NB, GB, ET, AB. "
    "Hint: python main.py --list-models"
)

E2002_MODEL_INIT_FAILED = (
    "[E2002] Failed to initialize model '{name}' with params {params}. "
    "Check that all parameters are valid for this model type."
)


# ── Parameter Errors (3xxx) ─────────────────────────────────────────────────────

E3001_INVALID_C = (
    "[E3001] Invalid value for --C: {value}. "
    "C must be a positive number. "
    "Example: --params C=1.0"
)

E3002_INVALID_N_NEIGHBORS = (
    "[E3002] Invalid value for --n_neighbors: {value}. "
    "n_neighbors must be a positive integer (>= 1). "
    "Example: --params n_neighbors=5"
)

E3003_INVALID_MAX_DEPTH = (
    "[E3003] Invalid value for --max_depth: {value}. "
    "max_depth must be a positive integer or omitted (None). "
    "Example: --params max_depth=10"
)

E3004_INVALID_KERNEL = (
    "[E3004] Invalid kernel: '{value}'. "
    "Available: linear, poly, rbf, sigmoid. "
    "Example: --params kernel=rbf"
)

E3005_INVALID_PARAM_FORMAT = (
    "[E3005] Invalid parameter format: '{pair}'. "
    "Expected KEY=VALUE. "
    "Example: --params C=1.0 kernel=rbf"
)


# ── System Errors (4xxx) ────────────────────────────────────────────────────────

E4001_OUTPUT_DIR = (
    "[E4001] Cannot create output directory: {path}. "
    "Check file permissions."
)

E4001_PLOT_FAILED = (
    "[E4001] Failed to save plot: {path}. "
    "Check disk space and file permissions."
)


def format_error(template: str, **kwargs) -> str:
    """Format an error template with provided values."""
    try:
        return template.format(**kwargs)
    except (KeyError, ValueError):
        return template  # Return raw template if formatting fails