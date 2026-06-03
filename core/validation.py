"""
core/validation.py — Dataset boundary validation

Validates X, y before they reach model training.
All validation functions raise DatasetValidationError with human-readable messages.
"""

import numpy as np


class DatasetValidationError(ValueError):
    """Raised when a dataset fails boundary validation checks."""
    pass


def validate_dataset(X, y, dataset_name="dataset"):
    """Validate dataset shape and content boundaries.

    Raises DatasetValidationError with actionable message on failure.
    """
    # Check 1: Empty dataset
    if X.size == 0 or len(X) == 0:
        raise DatasetValidationError(
            f"Error: {dataset_name} is empty. Provide at least 2 samples. "
            f"Example: python main.py --n-samples 500"
        )

    n_samples = len(X)

    # Check 2: Too few samples
    if n_samples < 2:
        raise DatasetValidationError(
            f"Error: {dataset_name} has only {n_samples} sample(s). "
            f"Need at least 2 samples for classification. "
            f"Example: python main.py --n-samples 500"
        )

    # Check 3: X and y length mismatch
    if len(y) != n_samples:
        raise DatasetValidationError(
            f"Error: X and y have mismatched lengths: "
            f"X has {n_samples} samples, but len(y)={len(y)}. "
            f"Ensure X and y have the same number of rows."
        )

    # Check 4: Single-class dataset
    unique_labels = np.unique(y)
    if len(unique_labels) < 2:
        labels_str = ", ".join(str(u) for u in unique_labels)
        raise DatasetValidationError(
            f"Error: Only 1 class ({labels_str}) found in labels for '{dataset_name}'. "
            f"Need at least 2 classes for classification. "
            f"Check your dataset or try a different seed."
        )

    # Check 5: All NaN or Inf in X
    if np.all(np.isnan(X)) or np.all(np.isinf(X)):
        raise DatasetValidationError(
            f"Error: {dataset_name} contains only NaN or Inf values. "
            f"Please check your data source."
        )

    # Check 6: Valid number check
    valid_mask = np.isfinite(X)
    if not np.any(valid_mask):
        raise DatasetValidationError(
            f"Error: {dataset_name} has no valid (finite) numeric values. "
            f"All feature values are NaN or Inf."
        )

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
                errors.append(
                    f"Error: Invalid value for --C: {C!r}. "
                    f"C must be a positive number. Example: --C 1.0"
                )
        except (TypeError, ValueError):
            errors.append(
                f"Error: Invalid value for --C: {C!r}. "
                f"C must be a number. Example: --C 1.0"
            )

    # KNN: n_neighbors must be positive integer
    if model_name == "KNN" and "n_neighbors" in params:
        k = params["n_neighbors"]
        try:
            k = int(k)
            if k < 1:
                errors.append(
                    f"Error: Invalid value for --n_neighbors: {k}. "
                    f"n_neighbors must be at least 1. Example: --params n_neighbors=5"
                )
        except (TypeError, ValueError):
            errors.append(
                f"Error: Invalid value for --n_neighbors: {k!r}. "
                f"n_neighbors must be an integer. Example: --params n_neighbors=5"
            )

    # Tree / RF / GB / ET: max_depth must be positive or None
    if model_name in ("Tree", "RF", "GB", "ET") and "max_depth" in params:
        md = params["max_depth"]
        if md is not None:
            try:
                md = int(md)
                if md < 1:
                    errors.append(
                        f"Error: Invalid value for --max_depth: {md}. "
                        f"max_depth must be a positive integer or omitted (None). "
                        f"Example: --params max_depth=10"
                    )
            except (TypeError, ValueError):
                errors.append(
                    f"Error: Invalid value for --max_depth: {md!r}. "
                    f"max_depth must be an integer. Example: --params max_depth=10"
                )

    if errors:
        raise ValueError("\n".join(errors))

    return True