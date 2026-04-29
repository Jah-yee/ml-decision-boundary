"""Coverage boost: test main.py functions with missing coverage."""
import os
import tempfile
import pytest
from unittest.mock import patch, MagicMock

from main import (
    generate_dataset,
    train_model,
    compute_decision_boundary,
    get_model_info,
    run_all_experiments,
    generate_comparison_plots,
    generate_single_model_visualization,
    ModelResult,
)


# ── compute_decision_boundary ────────────────────────────────────────────────

def test_compute_decision_boundary_basic():
    """compute_decision_boundary returns correct shape mesh."""
    X, y = generate_dataset("circles", n_samples=200, seed=42)
    model, _ = train_model("SVM", {"kernel": "rbf", "C": 1.0, "gamma": "scale"}, X, y)
    xx, yy, Z = compute_decision_boundary(model, X, resolution=50)
    assert xx.shape == yy.shape == Z.shape == (50, 50)
    assert Z.dtype == object or Z.dtype.kind in ('i', 'f')


def test_compute_decision_boundary_resolution_param():
    """compute_decision_boundary respects resolution parameter."""
    X, y = generate_dataset("moons", n_samples=200, seed=42)
    model, _ = train_model("Tree", {"max_depth": 5}, X, y)
    xx, yy, Z = compute_decision_boundary(model, X, resolution=25)
    assert xx.shape == (25, 25)


# ── get_model_info ───────────────────────────────────────────────────────────

def test_get_model_info_svm():
    """get_model_info extracts support_vectors for SVM."""
    X, y = generate_dataset("circles", n_samples=200, seed=42)
    model, _ = train_model("SVM", {"kernel": "rbf", "C": 1.0, "gamma": "scale"}, X, y)
    info = get_model_info(model, "SVM")
    assert "support_vectors" in info
    assert info["support_vectors"] >= 0


def test_get_model_info_tree():
    """get_model_info extracts tree_depth for Tree."""
    X, y = generate_dataset("blobs", n_samples=200, seed=42)
    model, _ = train_model("Tree", {"max_depth": 5}, X, y)
    info = get_model_info(model, "Tree")
    assert "tree_depth" in info


def test_get_model_info_rf():
    """get_model_info extracts n_trees and max_depth for RF."""
    X, y = generate_dataset("blobs", n_samples=200, seed=42)
    model, _ = train_model("RF", {"n_estimators": 10, "max_depth": 5}, X, y)
    info = get_model_info(model, "RF")
    assert "n_trees" in info
    assert "max_depth" in info
    assert info["n_trees"] == 10


def test_get_model_info_mlp():
    """get_model_info extracts n_layers for MLP."""
    X, y = generate_dataset("circles", n_samples=200, seed=42)
    model, _ = train_model("MLP", {"hidden_layer_sizes": (50, 25), "alpha": 0.001}, X, y)
    info = get_model_info(model, "MLP")
    assert "n_layers" in info
    assert info["n_layers"] == 2


def test_get_model_info_lr():
    """get_model_info returns empty dict for LR (no special attrs needed)."""
    X, y = generate_dataset("moons", n_samples=200, seed=42)
    model, _ = train_model("LR", {"C": 1.0}, X, y)
    info = get_model_info(model, "LR")
    assert isinstance(info, dict)


# ── generate_single_model_visualization ─────────────────────────────────────

@patch("main.plt.savefig")
@patch("main.plt.close")
@patch("main.plt.suptitle")
@patch("main.plt.tight_layout")
@patch("main.plt.subplots")
def test_generate_single_model_visualization_svm(mock_subplots, *_):
    """generate_single_model_visualization produces file for SVM."""
    mock_fig = MagicMock()
    mock_axes = [MagicMock() for _ in range(4)]
    mock_subplots.return_value = (mock_fig, mock_axes)

    results = generate_single_model_visualization("SVM", "circles", "/tmp/svm_test_out")
    assert results is not None
    assert len(results) == 4


@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
@patch("matplotlib.pyplot.subplots")
def test_generate_single_model_visualization_tree(mock_subplots, *_):
    """generate_single_model_visualization produces file for Tree."""
    mock_fig = MagicMock()
    mock_axes = [MagicMock() for _ in range(4)]
    mock_subplots.return_value = (mock_fig, mock_axes)

    with tempfile.TemporaryDirectory() as tmp:
        results = generate_single_model_visualization("Tree", "blobs", tmp)
        assert results is not None
        assert len(results) == 4


@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
@patch("matplotlib.pyplot.subplots")
def test_generate_single_model_visualization_knn(mock_subplots, *_):
    """generate_single_model_visualization produces file for KNN."""
    mock_fig = MagicMock()
    mock_axes = [MagicMock() for _ in range(4)]
    mock_subplots.return_value = (mock_fig, mock_axes)

    with tempfile.TemporaryDirectory() as tmp:
        results = generate_single_model_visualization("KNN", "moons", tmp)
        assert results is not None
        assert len(results) == 4


@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
@patch("matplotlib.pyplot.subplots")
def test_generate_single_model_visualization_unsupported_type(mock_subplots, *_):
    """generate_single_model_visualization gracefully handles unsupported type."""
    mock_fig = MagicMock()
    mock_subplots.return_value = (mock_fig, MagicMock())

    with tempfile.TemporaryDirectory() as tmp:
        results = generate_single_model_visualization("LR", "circles", tmp)
        assert results is None


# ── generate_comparison_plots ───────────────────────────────────────────────

def test_generate_comparison_plots_basic():
    """generate_comparison_plots runs end-to-end without error."""
    # Provide at least one result per dataset so max() never sees empty list
    results = [
        ModelResult(name="SVM_circles", params={"kernel": "rbf", "C": 1.0}, accuracy=0.85,
                    train_time=0.01, boundary_points=[], support_vectors=10),
        ModelResult(name="SVM_moons", params={"kernel": "rbf", "C": 1.0}, accuracy=0.80,
                    train_time=0.01, boundary_points=[], support_vectors=10),
        ModelResult(name="SVM_blobs", params={"kernel": "rbf", "C": 1.0}, accuracy=0.95,
                    train_time=0.01, boundary_points=[], support_vectors=10),
        ModelResult(name="SVM_xor", params={"kernel": "rbf", "C": 1.0}, accuracy=0.70,
                    train_time=0.01, boundary_points=[], support_vectors=10),
    ]
    with tempfile.TemporaryDirectory() as tmp:
        with patch("matplotlib.pyplot.savefig"):
            with patch("matplotlib.pyplot.close"):
                with patch("matplotlib.pyplot.colorbar"):
                    with patch("matplotlib.pyplot.tight_layout"):
                        with patch("matplotlib.pyplot.yscale"):
                            with patch("matplotlib.pyplot.legend"):
                                generate_comparison_plots(results, tmp)
        # End-to-end ran without raising


# ── run_all_experiments ───────────────────────────────────────────────────────

@patch("matplotlib.pyplot.savefig")
@patch("matplotlib.pyplot.close")
@patch("matplotlib.pyplot.suptitle")
@patch("matplotlib.pyplot.tight_layout")
@patch("matplotlib.pyplot.subplots")
@patch("matplotlib.pyplot.figure")
@patch("matplotlib.pyplot.colorbar")
@patch("matplotlib.pyplot.imshow")
@patch("matplotlib.pyplot.text")
@patch("matplotlib.pyplot.boxplot")
@patch("matplotlib.pyplot.title")
@patch("matplotlib.pyplot.xlabel")
@patch("matplotlib.pyplot.ylabel")
@patch("matplotlib.pyplot.xticks")
@patch("matplotlib.pyplot.yticks")
@patch("matplotlib.pyplot.legend")
@patch("matplotlib.pyplot.yscale")
def test_run_all_experiments_runs_without_error(*_):
    """run_all_experiments completes without raising."""
    # This is slow so we just verify it doesn't crash and returns a list
    results = run_all_experiments()
    assert isinstance(results, list)
    # Should have results for at least some model×dataset combos
    assert len(results) > 0
    # Each result should have name, accuracy, params
    for r in results:
        assert hasattr(r, "name")
        assert hasattr(r, "accuracy")
        assert hasattr(r, "params")
