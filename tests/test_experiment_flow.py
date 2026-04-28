"""
Tests for run_experiment, save_results, and related high-value flows.
Goal: lift main.py coverage from 27% toward 50%+.
"""
import pytest
import json
import os
import tempfile
from pathlib import Path

from main import (
    generate_dataset,
    run_experiment,
    save_results,
    ModelResult,
)


class TestRunExperiment:
    """Test run_experiment: dataset → train → eval → ModelResult"""

    @pytest.mark.parametrize("dataset", ["circles", "moons", "blobs", "xor"])
    def test_run_experiment_returns_model_result(self, dataset):
        result = run_experiment(dataset, "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42)
        assert isinstance(result, ModelResult)
        assert 0.0 <= result.accuracy <= 1.0
        assert result.train_time >= 0
        assert result.name == f"SVM_{dataset}"
        assert isinstance(result.params, dict)
        assert isinstance(result.boundary_points, list)

    @pytest.mark.parametrize("model_type,params", [
        ("LR", {"C": 1.0}),
        ("Tree", {"max_depth": 3}),
        ("RF", {"n_estimators": 5, "max_depth": 3}),
        ("KNN", {"n_neighbors": 3}),
        ("MLP", {"hidden_layer_sizes": (50,)}),
        ("NB", {}),
    ])
    def test_run_experiment_various_models(self, model_type, params):
        result = run_experiment("circles", model_type, params, seed=42)
        assert isinstance(result, ModelResult)
        assert 0.0 <= result.accuracy <= 1.0
        assert result.train_time >= 0

    def test_run_experiment_circles_svm_rbf_is_reasonable(self):
        """SVM RBF on circles should achieve >0.6 accuracy with default params."""
        result = run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf", "gamma": "scale"}, seed=42)
        assert result.accuracy >= 0.6, f"SVM RBF on circles should be >=0.6, got {result.accuracy}"

    def test_run_experiment_xor_tree_deep_is_reasonable(self):
        """Tree with depth=10 on xor should achieve >0.5 accuracy."""
        result = run_experiment("xor", "Tree", {"max_depth": 10}, seed=42)
        assert result.accuracy >= 0.5, f"Tree(depth=10) on xor should be >=0.5, got {result.accuracy}"

    def test_run_experiment_model_result_has_model_info(self):
        """SVM result should have support_vectors; Tree should have tree_depth."""
        svm_result = run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42)
        assert hasattr(svm_result, "support_vectors")
        assert svm_result.support_vectors is not None

        tree_result = run_experiment("xor", "Tree", {"max_depth": 5}, seed=42)
        assert hasattr(tree_result, "tree_depth")
        assert tree_result.tree_depth is not None

    def test_run_experiment_unknown_model_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            run_experiment("circles", "UnknownModel", {}, seed=42)

    def test_run_experiment_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset"):
            run_experiment("unknown_dataset", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42)


class TestSaveResults:
    """Test save_results: writes valid JSON with expected schema."""

    def test_save_results_creates_file(self):
        results = [
            run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42),
            run_experiment("moons", "LR", {"C": 1.0}, seed=42),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            save_results(results, str(output_path))
            assert output_path.exists(), "save_results should create file"

    def test_save_results_valid_json(self):
        results = [
            run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            save_results(results, str(output_path))
            with open(output_path) as f:
                data = json.load(f)
            assert "experiments" in data
            assert "summary" in data

    def test_save_results_summary_fields(self):
        results = [
            run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42),
            run_experiment("circles", "LR", {"C": 1.0}, seed=42),
        ]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            save_results(results, str(output_path))
            with open(output_path) as f:
                data = json.load(f)
            summary = data["summary"]
            assert summary["total_experiments"] == 2
            assert "best_accuracy" in summary
            assert "fastest_train_time" in summary
            assert "model_types" in summary
            assert "datasets" in summary

    def test_save_results_experiment_has_required_fields(self):
        results = [run_experiment("circles", "SVM", {"C": 1.0, "kernel": "rbf"}, seed=42)]
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "results.json"
            save_results(results, str(output_path))
            with open(output_path) as f:
                data = json.load(f)
            exp = data["experiments"][0]
            assert "name" in exp
            assert "accuracy" in exp
            assert "train_time" in exp
            assert "params" in exp

    def test_save_results_empty_list(self):
        """Empty results list should still produce valid JSON."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_path = Path(tmpdir) / "empty.json"
            save_results([], str(output_path))
            with open(output_path) as f:
                data = json.load(f)
            assert data["summary"]["total_experiments"] == 0
            assert data["experiments"] == []
            # best/fastest should still be present (NaN when empty)
            import math
            assert math.isnan(data["summary"]["best_accuracy"])
            assert math.isnan(data["summary"]["fastest_train_time"])
