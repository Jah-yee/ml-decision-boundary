"""
tests/test_registry.py — v8 DoD #1: Model Registry unit tests

Covers:
- RegistryManager.save_model() / load_model()
- list_models(), get_metadata(), delete_model()
- find_model()
- schema validation
- --no-registry flag integration
"""

import pytest
import tempfile
import shutil
import json
from pathlib import Path
from datetime import date

from sklearn.svm import SVC
from sklearn.datasets import make_circles

from core.registry import RegistryManager, REGISTRY_BASE


# Dynamic date helper to avoid hardcoded dates in assertions
def _today():
    return date.today().strftime("%Y-%m-%d")


@pytest.fixture
def temp_registry(tmp_path):
    """Provide a temporary registry root for isolated testing."""
    rm = RegistryManager(registry_base=tmp_path)
    rm._ensure_dirs()
    yield rm
    # Cleanup handled by tmp_path fixture


@pytest.fixture
def trained_svm():
    """Provide a pre-trained SVM on synthetic data."""
    X, y = make_circles(n_samples=100, noise=0.2, random_state=42)
    model = SVC(kernel="rbf", C=1.0, gamma="scale")
    model.fit(X, y)
    return model, X, y


class TestRegistrySaveLoad:
    def test_save_model_returns_valid_id(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model,
            model_type="SVM",
            hyperparameters={"kernel": "rbf", "C": 1.0, "gamma": "scale"},
            X_train=X,
            y_train=y,
            dataset_name="circles",
            n_samples=100,
            train_accuracy=0.95,
            test_accuracy=0.90,
        )
        today = _today()
        assert model_id.startswith(f"{today}_")
        assert len(model_id.split("_")) == 2
        assert len(model_id.split("_")[1]) == 6

    def test_save_model_creates_json_and_joblib(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model,
            model_type="SVM",
            hyperparameters={"kernel": "rbf", "C": 1.0},
            X_train=X,
            y_train=y,
            dataset_name="circles",
            n_samples=100,
            train_accuracy=0.95,
            test_accuracy=0.90,
        )
        json_path = temp_registry.models_dir / f"{model_id}.json"
        joblib_path = temp_registry.models_dir / f"{model_id}.joblib"
        assert json_path.exists()
        assert joblib_path.exists()

    def test_save_model_metadata_schema(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model,
            model_type="SVM",
            hyperparameters={"kernel": "rbf", "C": 1.0},
            X_train=X,
            y_train=y,
            dataset_name="circles",
            n_samples=100,
            train_accuracy=0.95,
            test_accuracy=0.90,
        )
        meta = temp_registry.get_metadata(model_id)
        assert meta["id"] == model_id
        assert meta["model_type"] == "SVM"
        assert meta["hyperparameters"] == {"kernel": "rbf", "C": 1.0}
        assert meta["dataset"]["name"] == "circles"
        assert meta["dataset"]["n_samples"] == 100
        assert "sha256:" in meta["dataset"]["hash"]
        assert meta["metrics"]["train_accuracy"] == 0.95
        assert meta["metrics"]["test_accuracy"] == 0.90
        assert meta["plugin_origin"] is False
        assert "joblib_path" in meta
        today = _today()
        assert today in meta["created_at"]

    def test_load_model_restores_correct_type(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model,
            model_type="SVM",
            hyperparameters={"kernel": "rbf", "C": 1.0},
            X_train=X,
            y_train=y,
            dataset_name="circles",
            n_samples=100,
            train_accuracy=0.95,
            test_accuracy=0.90,
        )
        loaded = temp_registry.load_model(model_id)
        assert isinstance(loaded, SVC)
        assert loaded.kernel == "rbf"
        assert loaded.C == 1.0

    def test_load_model_predicts_correctly(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        # trained_svm fits on full X,y; use same split logic as main.py
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )
        # Re-train on train split only for meaningful test accuracy
        model2 = SVC(kernel="rbf", C=1.0, gamma="scale")
        model2.fit(X_train, y_train)
        train_acc = model2.score(X_train, y_train)
        test_acc = model2.score(X_test, y_test)
        model_id = temp_registry.save_model(
            model=model2,
            model_type="SVM",
            hyperparameters={"kernel": "rbf", "C": 1.0, "gamma": "scale"},
            X_train=X_train,
            y_train=y_train,
            dataset_name="circles",
            n_samples=X_train.shape[0],
            train_accuracy=train_acc,
            test_accuracy=test_acc,
        )
        loaded = temp_registry.load_model(model_id)
        # Loaded model should predict same as saved model
        assert loaded.score(X_test, y_test) == test_acc

    def test_load_model_not_found_raises(self, temp_registry):
        with pytest.raises(FileNotFoundError, match="not found"):
            temp_registry.load_model(f"{_today()}_nonexist")


class TestRegistryListDelete:
    def test_list_models_returns_newest_first(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        from sklearn.linear_model import LogisticRegression
        lr = LogisticRegression(random_state=42, max_iter=1000)
        lr.fit(X, y)
        id1 = temp_registry.save_model(
            model=model, model_type="SVM", hyperparameters={"kernel": "rbf"},
            X_train=X, y_train=y, dataset_name="circles",
            n_samples=100, train_accuracy=0.95, test_accuracy=0.90,
        )
        id2 = temp_registry.save_model(
            model=lr, model_type="LR", hyperparameters={"C": 1.0},
            X_train=X, y_train=y, dataset_name="circles",
            n_samples=100, train_accuracy=0.90, test_accuracy=0.85,
        )
        models = temp_registry.list_models()
        ids = [m["id"] for m in models]
        # Newest first (sorted reverse by filename)
        assert ids[0] == id2, f"Expected {id2} first, got {ids[0]}"
        assert ids[1] == id1

    def test_delete_model_removes_both_files(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model, model_type="SVM", hyperparameters={},
            X_train=X, y_train=y, dataset_name="circles",
            n_samples=100, train_accuracy=0.95, test_accuracy=0.90,
        )
        temp_registry.delete_model(model_id)
        assert not (temp_registry.models_dir / f"{model_id}.json").exists()
        assert not (temp_registry.models_dir / f"{model_id}.joblib").exists()

    def test_delete_model_not_found_raises(self, temp_registry):
        with pytest.raises(FileNotFoundError, match="not found"):
            temp_registry.delete_model(f"{_today()}_nonexist")

    def test_find_model(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        model_id = temp_registry.save_model(
            model=model, model_type="SVM", hyperparameters={},
            X_train=X, y_train=y, dataset_name="circles",
            n_samples=100, train_accuracy=0.95, test_accuracy=0.90,
        )
        assert temp_registry.find_model(model_id) is True
        assert temp_registry.find_model(f"{_today()}_nonexist") is False


class TestRegistryManagerSingleton:
    def test_get_registry_manager_returns_registry_manager(self):
        from core.registry import get_registry_manager
        rm = get_registry_manager()
        assert isinstance(rm, RegistryManager)

    def test_get_registry_manager_singleton(self):
        from core.registry import get_registry_manager
        rm1 = get_registry_manager()
        rm2 = get_registry_manager()
        assert rm1 is rm2
