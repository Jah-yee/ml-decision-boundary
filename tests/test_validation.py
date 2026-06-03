"""
tests/test_validation.py — Dataset boundary validation tests

Covers v7 DoD #2: validate_dataset and validate_model_params.
"""

import pytest
import numpy as np
from core.validation import (
    validate_dataset,
    validate_model_params,
    DatasetValidationError,
)


# ─────────────────────────────────────────────────────────────────────────────
# validate_dataset — empty / too-small
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_empty_X():
    """Empty X array raises DatasetValidationError."""
    X = np.array([]).reshape(0, 2)
    y = np.array([])
    with pytest.raises(DatasetValidationError, match="is empty"):
        validate_dataset(X, y, "test_ds")


def test_validate_X_too_few_samples():
    """X with 1 sample raises DatasetValidationError."""
    X = np.random.randn(1, 2)
    y = np.array([0])
    with pytest.raises(DatasetValidationError, match="only 1 sample"):
        validate_dataset(X, y, "test_ds")


def test_validate_length_mismatch():
    """X and y with different lengths raises DatasetValidationError."""
    X = np.random.randn(10, 2)
    y = np.array([0, 1] * 4)  # 8 elements
    with pytest.raises(DatasetValidationError, match="mismatched lengths"):
        validate_dataset(X, y, "test_ds")


# ─────────────────────────────────────────────────────────────────────────────
# validate_dataset — single-class
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_single_class():
    """y with only one unique label raises DatasetValidationError."""
    X = np.random.randn(10, 2)
    y = np.zeros(10, dtype=int)  # all label=0
    with pytest.raises(DatasetValidationError, match="Only 1 class"):
        validate_dataset(X, y, "test_ds")


def test_validate_single_class_explicit():
    """y with one non-zero label still fails."""
    X = np.random.randn(10, 2)
    y = np.ones(10, dtype=int)  # all label=1
    with pytest.raises(DatasetValidationError, match="Only 1 class"):
        validate_dataset(X, y, "test_ds")


# ─────────────────────────────────────────────────────────────────────────────
# validate_dataset — NaN / Inf
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_all_nan():
    """All-NaN X raises DatasetValidationError."""
    X = np.array([[np.nan, np.nan]] * 10)
    y = np.array([0, 1] * 5)
    with pytest.raises(DatasetValidationError, match="only NaN or Inf"):
        validate_dataset(X, y, "test_ds")


def test_validate_all_inf():
    """All-Inf X raises DatasetValidationError."""
    X = np.array([[np.inf, -np.inf]] * 10)
    y = np.array([0, 1] * 5)
    with pytest.raises(DatasetValidationError, match="only NaN or Inf"):
        validate_dataset(X, y, "test_ds")


def test_validate_no_finite_values():
    """X with no finite values raises DatasetValidationError."""
    X = np.array([[np.nan, np.inf]] * 10)
    y = np.array([0, 1] * 5)
    with pytest.raises(DatasetValidationError, match="no valid"):
        validate_dataset(X, y, "test_ds")


# ─────────────────────────────────────────────────────────────────────────────
# validate_dataset — valid inputs pass silently
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_normal_dataset_passes():
    """Normal 2-class dataset passes without error."""
    X = np.random.randn(100, 2)
    y = np.array([0] * 50 + [1] * 50)
    # should not raise
    validate_dataset(X, y, "test_ds")


# ─────────────────────────────────────────────────────────────────────────────
# validate_model_params — SVM / LR C
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_SVM_C_negative():
    """SVM with negative C raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --C"):
        validate_model_params("SVM", {"C": -1.0})


def test_validate_SVM_C_zero():
    """SVM with C=0 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --C"):
        validate_model_params("SVM", {"C": 0})


def test_validate_SVM_C_positive_passes():
    """SVM with positive C passes."""
    validate_model_params("SVM", {"C": 1.0})
    validate_model_params("SVM", {"C": 0.001})
    validate_model_params("SVM", {"C": 1000.0})


def test_validate_LR_C_invalid_string():
    """LR with non-numeric C raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --C"):
        validate_model_params("LR", {"C": "bad"})


# ─────────────────────────────────────────────────────────────────────────────
# validate_model_params — KNN n_neighbors
# ─────────────────────────────────────────────────────────────────────────────

def test_validate_KNN_k_zero():
    """KNN with k=0 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --n_neighbors"):
        validate_model_params("KNN", {"n_neighbors": 0})


def test_validate_KNN_k_negative():
    """KNN with k=-1 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --n_neighbors"):
        validate_model_params("KNN", {"n_neighbors": -1})


def test_validate_KNN_k_valid():
    """KNN with k>=1 passes."""
    validate_model_params("KNN", {"n_neighbors": 1})
    validate_model_params("KNN", {"n_neighbors": 50})


# ─────────────────────────────────────────────────────────────────────────────
# validate_model_params — Tree/RF/GB/ET max_depth
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("model", ["Tree", "RF", "GB", "ET"])
def test_validate_max_depth_zero(model):
    """max_depth=0 raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --max_depth"):
        validate_model_params(model, {"max_depth": 0})


@pytest.mark.parametrize("model", ["Tree", "RF", "GB", "ET"])
def test_validate_max_depth_negative(model):
    """max_depth negative raises ValueError."""
    with pytest.raises(ValueError, match="Invalid value for --max_depth"):
        validate_model_params(model, {"max_depth": -1})


@pytest.mark.parametrize("model", ["Tree", "RF", "GB", "ET"])
def test_validate_max_depth_none_passes(model):
    """max_depth=None passes (no limit)."""
    validate_model_params(model, {"max_depth": None})


@pytest.mark.parametrize("model", ["Tree", "RF", "GB", "ET"])
def test_validate_max_depth_positive_passes(model):
    """max_depth positive passes."""
    validate_model_params(model, {"max_depth": 10})


# ─────────────────────────────────────────────────────────────────────────────
# Integration: run_experiment surfaces validation errors cleanly
# ─────────────────────────────────────────────────────────────────────────────

def test_run_experiment_rejects_bad_model_params():
    """run_experiment with invalid params raises DatasetValidationError / ValueError."""
    from main import run_experiment
    with pytest.raises(ValueError, match="Invalid value"):
        run_experiment("circles", "SVM", {"C": -1.0}, seed=42)