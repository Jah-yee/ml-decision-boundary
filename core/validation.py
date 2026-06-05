"""
core/validation.py — Dataset boundary validation

Validates X, y before they reach model training.
All validation functions raise DatasetValidationError with human-readable messages.
Uses canonical error codes from core/error_messages.py.
"""

import numpy as np

from core.error_messages import (
    E1001_EMPTY, E1002_TOO_FEW, E1003_LENGTH_MISMATCH,
    E1004_SINGLE_CLASS, E1005_ALL_NAN_INF, E1006_NO_VALID_VALUES,
    E3001_INVALID_C, E3002_INVALID_N_NEIGHBORS, E3003_INVALID_MAX_DEPTH,
    format_error,
)


class DatasetValidationError(ValueError):
    """Raised when a dataset fails boundary validation checks."""
    pass


def validate_dataset(X, y, dataset_name="dataset"):
    """Validate dataset shape and content boundaries.

    Raises DatasetValidationError with actionable message on failure.
    """
    # Check 1: Empty dataset
    if X.size == 0 or len(X) == 0:
        raise DatasetValidationError(E1001_EMPTY)

    n_samples = len(X)

    # Check 2: Too few samples
    if n_samples < 2:
        raise DatasetValidationError(format_error(E1002_TOO_FEW, n=n_samples))

    # Check 3: X and y length mismatch
    if len(y) != n_samples:
        raise DatasetValidationError(format_error(
            E1003_LENGTH_MISMATCH, n_x=n_samples, n_y=len(y)
        ))

    # Check 4: Single-class dataset
    unique_labels = np.unique(y)
    if len(unique_labels) < 2:
        labels_str = ", ".join(str(u) for u in unique_labels)
        raise DatasetValidationError(format_error(
            E1004_SINGLE_CLASS, dataset=dataset_name, labels=labels_str
        ))

    # Check 5: All NaN or Inf in X
    if np.all(np.isnan(X)) or np.all(np.isinf(X)):
        raise DatasetValidationError(E1005_ALL_NAN_INF)

    # Check 6: Valid number check
    valid_mask = np.isfinite(X)
    if not np.any(valid_mask):
        raise DatasetValidationError(E1006_NO_VALID_VALUES)

    return True


def validate_model_params(model_name, params):
    """Validate model hyperparameters.

    Raises ValueError with actionable message for invalid params.
    """
    errors = []

    # SVM / LR: C must be positive
    if model_name in ("SVM", "LR") and "C" in params:
        C = params["C"]
        try:
            C = float(C)
            if C <= 0:
                errors.append(format_error(E3001_INVALID_C, value=C))
        except (TypeError, ValueError):
            errors.append(format_error(E3001_INVALID_C, value=C))

    # KNN: n_neighbors must be positive integer
    if model_name == "KNN" and "n_neighbors" in params:
        k = params["n_neighbors"]
        try:
            k = int(k)
            if k < 1:
                errors.append(format_error(E3002_INVALID_N_NEIGHBORS, value=k))
        except (TypeError, ValueError):
            errors.append(format_error(E3002_INVALID_N_NEIGHBORS, value=k))

    # Tree / RF / GB / ET: max_depth must be positive or None
    if model_name in ("Tree", "RF", "GB", "ET") and "max_depth" in params:
        md = params["max_depth"]
        if md is not None:
            try:
                md = int(md)
                if md < 1:
                    errors.append(format_error(E3003_INVALID_MAX_DEPTH, value=md))
            except (TypeError, ValueError):
                errors.append(format_error(E3003_INVALID_MAX_DEPTH, value=md))

    if errors:
        raise ValueError("\n".join(errors))

    return True