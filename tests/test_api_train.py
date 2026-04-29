"""Tests for api/train.py pure functions"""

import pytest
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.train import (
    build_model,
    slider_to_params,
    get_model_info_dict,
    DATASET_GENERATORS,
)


class TestBuildModel:
    def test_build_svm(self):
        model = build_model("SVM", {"kernel": "rbf", "C": 1.0})
        assert model.kernel == "rbf"
        assert model.C == 1.0

    def test_build_lr(self):
        model = build_model("LR", {"C": 1.0})
        assert model.C == 1.0

    def test_build_tree(self):
        model = build_model("Tree", {"max_depth": 5})
        assert model.max_depth == 5

    def test_build_rf(self):
        model = build_model("RF", {"n_estimators": 10, "max_depth": 5})
        assert model.n_estimators == 10

    def test_build_knn(self):
        model = build_model("KNN", {"n_neighbors": 5})
        assert model.n_neighbors == 5

    def test_build_mlp(self):
        model = build_model("MLP", {"hidden_layer_sizes": (50,)})
        assert model.hidden_layer_sizes == (50,)

    def test_build_unknown_raises(self):
        with pytest.raises(ValueError, match="Unknown model"):
            build_model("UNKNOWN", {})


class TestSliderToParams:
    def test_svm_params(self):
        params = slider_to_params("SVM", 50, 50)
        assert params["kernel"] == "rbf"
        assert "C" in params
        assert "gamma" in params

    def test_lr_params(self):
        params = slider_to_params("LR", 50, 50)
        assert "C" in params

    def test_tree_params(self):
        params = slider_to_params("Tree", 50, 50)
        assert "max_depth" in params
        assert "min_samples_split" in params

    def test_rf_params(self):
        params = slider_to_params("RF", 50, 50)
        assert "n_estimators" in params
        assert "max_depth" in params

    def test_knn_params(self):
        params = slider_to_params("KNN", 50, 50)
        assert "n_neighbors" in params
        assert params["n_neighbors"] >= 1

    def test_mlp_params(self):
        params = slider_to_params("MLP", 50, 50)
        assert "hidden_layer_sizes" in params
        assert "alpha" in params


class TestDatasetGenerators:
    def test_circles_shape(self):
        X, y = DATASET_GENERATORS["circles"](100, 0.1, seed=42)
        assert X.shape == (100, 2)
        assert y.shape == (100,)

    def test_moons_shape(self):
        X, y = DATASET_GENERATORS["moons"](100, 0.1, seed=42)
        assert X.shape == (100, 2)

    def test_blobs_shape(self):
        X, y = DATASET_GENERATORS["blobs"](100, 0.1, seed=42)
        assert X.shape[1] == 2

    def test_xor_shape(self):
        X, y = DATASET_GENERATORS["xor"](100, 0.1, seed=42)
        assert X.shape == (100, 2)
        assert y.shape == (100,)


class TestGetModelInfoDict:
    def test_svm_info(self):
        from sklearn.svm import SVC
        X, y = DATASET_GENERATORS["circles"](100, 0.1, seed=42)
        model = SVC(kernel="rbf", C=1.0).fit(X, y)
        info = get_model_info_dict(model, "SVM")
        assert "Support Vectors" in info
        assert "Kernel" in info

    def test_tree_info(self):
        from sklearn.tree import DecisionTreeClassifier
        X, y = DATASET_GENERATORS["circles"](100, 0.1, seed=42)
        model = DecisionTreeClassifier(max_depth=5, random_state=42).fit(X, y)
        info = get_model_info_dict(model, "Tree")
        assert "Tree Depth" in info
        assert "Leaves" in info
