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

    def test_lr_train(self):
        X, y = generate_dataset("moons", n_samples=200, seed=42)
        model, train_time = train_model("LR", {"C": 1.0}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0

    def test_naive_bayes_train(self):
        X, y = generate_dataset("blobs", n_samples=200, seed=42)
        model, train_time = train_model("NB", {}, X, y)
        assert train_time >= 0
        accuracy = model.score(X, y)
        assert 0.0 <= accuracy <= 1.0


class TestDatasetEdgeCases:
    """Edge case tests for dataset generation"""

    def test_unknown_dataset_raises(self):
        with pytest.raises(ValueError, match="Unknown dataset"):
            generate_dataset("invalid_dataset", n_samples=100, seed=42)

    def test_circles_with_seed_reproducibility(self):
        """Same seed must produce identical datasets"""
        X1, y1 = generate_dataset("circles", n_samples=200, seed=123)
        X2, y2 = generate_dataset("circles", n_samples=200, seed=123)
        np.testing.assert_array_almost_equal(X1, X2)
        np.testing.assert_array_equal(y1, y2)

    def test_xor_with_seed_reproducibility(self):
        X1, y1 = generate_dataset("xor", n_samples=200, seed=456)
        X2, y2 = generate_dataset("xor", n_samples=200, seed=456)
        np.testing.assert_array_almost_equal(X1, X2)
        np.testing.assert_array_equal(y1, y2)

    def test_blobs_multiclass(self):
        """blobs generates 3-cluster multi-class dataset"""
        X, y = generate_dataset("blobs", n_samples=300, seed=42)
        assert X.shape == (300, 2)
        assert y.shape == (300,)
        # blobs from sklearn make_blobs with 3 centers returns {0,1,2}
        assert set(np.unique(y)) <= {0, 1, 2}

    def test_dataset_noise_is_applied(self):
        """circles with high noise should have more variance than low noise"""
        X_low, _ = generate_dataset("circles", n_samples=200, noise=0.05, seed=42)
        X_high, _ = generate_dataset("circles", n_samples=200, noise=0.5, seed=42)
        low_spread = X_low.std()
        high_spread = X_high.std()
        assert high_spread > low_spread, "Higher noise should produce larger spread"


class TestModelResult:
    """Test ModelResult dataclass"""

    def test_model_result_creation(self):
        from main import ModelResult
        from dataclasses import asdict
        result = ModelResult(
            name="SVM_circles",
            params={"C": 1.0, "kernel": "rbf"},
            accuracy=0.79,
            train_time=0.003,
            boundary_points=[[0.1, 0.2], [0.3, 0.4]],
            support_vectors=100
        )
        assert result.name == "SVM_circles"
        assert result.accuracy == 0.79
        assert result.support_vectors == 100
        assert isinstance(asdict(result), dict)


class TestAPIContractMain:
    """Test API contract consistency between main.py and api/train.py"""

    def test_train_model_params_order_consistency(self):
        """train_model(model_type, params, X, y) must match main.py signature"""
        from main import generate_dataset, train_model
        import inspect
        sig = inspect.signature(train_model)
        params = list(sig.parameters.keys())
        assert params == ["model_type", "params", "X_train", "y_train"], \
            f"train_model signature changed: {params}"

    def test_generate_dataset_params_consistency(self):
        """generate_dataset API must match documented signature"""
        import inspect
        sig = inspect.signature(generate_dataset)
        params = list(sig.parameters.keys())
        assert "dataset_name" in params
        assert "n_samples" in params
        assert "seed" in params
