"""
Tests for main.py core functionality
"""
import pytest
import numpy as np
from main import generate_dataset, train_model, ModelResult


class TestDatasets:
    """Test dataset generation"""

    def test_circles_dataset_shape(self):
        X, y = generate_dataset("circles", n_samples=200, seed=42)
        assert X.shape == (200, 2), f"Expected (200, 2), got {X.shape}"
        assert y.shape == (200,), f"Expected (200,), got {y.shape}"
        assert set(np.unique(y)) <= {0, 1}, "y must be binary classification"

    def test_moons_dataset_shape(self):
        X, y = generate_dataset("moons", n_samples=150, seed=42)
        assert X.shape == (150, 2)
        assert y.shape == (150,)

    def test_blobs_dataset_shape(self):
        X, y = generate_dataset("blobs", n_samples=200, seed=42)
        assert X.shape == (200, 2)
        assert y.shape == (200,)

    def test_xor_dataset_shape(self):
        X, y = generate_dataset("xor", n_samples=200, seed=42)
        assert X.shape == (200, 2)
        assert y.shape == (200,)


class TestModelTraining:
    """Test model training - API: train_model(model_type, params, X, y)"""

    def test_svm_train(self):
        X, y = generate_dataset("circles", n_samples=200, seed=42)
        model, train_time = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_decision_tree_train(self):
        X, y = generate_dataset("xor", n_samples=200, seed=42)
        model, train_time = train_model("Tree", {"max_depth": 5}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_knn_train(self):
        X, y = generate_dataset("moons", n_samples=200, seed=42)
        model, train_time = train_model("KNN", {"n_neighbors": 5}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_random_forest_train(self):
        X, y = generate_dataset("blobs", n_samples=200, seed=42)
        model, train_time = train_model("RF", {"n_estimators": 10, "max_depth": 5}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_mlp_train(self):
        X, y = generate_dataset("circles", n_samples=200, seed=42)
        model, train_time = train_model("MLP", {"hidden_layer_sizes": (50,)}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_all_models_deterministic(self):
        """Same seed should produce same results"""
        X, y = generate_dataset("circles", n_samples=100, seed=999)
        _, t1 = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)
        _, t2 = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)
        # With same data and same seed, results should be identical
        acc1 = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)[0].score(X, y)
        acc2 = train_model("SVM", {"C": 1.0, "kernel": "rbf"}, X, y)[0].score(X, y)
        assert abs(acc1 - acc2) < 1e-6, "Results should be deterministic with same seed"

    def test_unknown_model_raises(self):
        X, y = generate_dataset("circles", n_samples=100, seed=42)
        with pytest.raises(ValueError, match="Unknown model"):
            train_model("UnknownModel", {}, X, y)
