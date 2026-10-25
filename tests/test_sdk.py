"""
tests/test_sdk.py — v12 DoD #1: Python SDK (ml_db) test suite

Covers the acceptance criteria from ADR-0017:
  - `from ml_db import MLDB; m = MLDB()` instantiable
  - `m.train(...)` returns a training result
  - `m.predict(...)` returns predictions
  - registry integration (list / tag / compare)
  - error contract (unknown dataset / model / missing model)
"""

import numpy as np
import pytest

from ml_db import (
    InvalidInputError,
    MLDB,
    MLDBError,
    ModelNotFoundError,
    TrainResult,
    UnknownDatasetError,
    UnknownModelError,
)


@pytest.fixture
def db(tmp_path):
    """MLDB instance backed by an isolated registry directory."""
    return MLDB(registry_base=tmp_path / "registry")


# ── Top-level API ────────────────────────────────────────────────────────────

def test_top_level_import_exposes_mldb():
    import ml_db

    assert hasattr(ml_db, "MLDB")
    assert ml_db.__version__


def test_mldb_is_instantiable(db):
    assert isinstance(db, MLDB)
    assert db.registry is not None


def test_datasets_and_models_are_enumerated(db):
    datasets = db.datasets()
    models = db.models()
    assert "circles" in datasets
    assert "swiss_roll" in datasets
    assert "SVM" in models
    assert "RF" in models


# ── Training ─────────────────────────────────────────────────────────────────

def test_train_returns_result_with_metrics(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)

    assert isinstance(result, TrainResult)
    assert result.model_type == "SVM"
    assert result.dataset == "circles"
    assert 0.0 <= result.accuracy <= 1.0
    assert 0.0 <= result.train_accuracy <= 1.0
    assert result.train_time >= 0.0
    assert result.model_id  # registered by default


def test_train_can_skip_registration(db):
    result = db.train(model="Tree", dataset="moons", n_samples=200, register=False)
    assert result.model_id == ""
    assert db.list_models() == []


def test_train_registers_model_in_registry(db):
    result = db.train(model="RF", dataset="blobs", n_samples=200)
    metadata = db.get_model(result.model_id)
    assert metadata["model_type"] == "RF"
    assert metadata["dataset"]["name"] == "blobs"
    assert any(m["id"] == result.model_id for m in db.list_models())


def test_train_with_tags(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200, tags=["sdk-demo"])
    tagged = db.list_models_by_tag("sdk-demo")
    assert len(tagged) == 1
    assert tagged[0]["id"] == result.model_id
    assert "sdk-demo" in db.list_tags()


def test_train_is_deterministic_for_fixed_seed(db):
    a = db.train(model="SVM", dataset="circles", n_samples=200, register=False)
    b = db.train(model="SVM", dataset="circles", n_samples=200, register=False)
    assert a.accuracy == b.accuracy


# ── Inference ────────────────────────────────────────────────────────────────

def test_predict_with_registered_model(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)
    preds = db.predict(result.model_id, X=[[0.0, 0.0], [1.0, 1.0]])
    assert len(preds) == 2
    assert all(p in (0, 1) for p in preds)


def test_predict_with_in_memory_estimator(db):
    result = db.train(model="Tree", dataset="moons", n_samples=200, register=False)
    preds = db.predict(model=result.model, X=[[0.0, 0.0], [2.0, 2.0]])
    assert len(preds) == 2


def test_predict_batch_returns_structured_payload(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)
    payload = db.predict_batch(result.model_id, X=[[0.0, 0.0], [1.0, 1.0], [2.0, 2.0]])
    assert payload["count"] == 3
    assert len(payload["predictions"]) == 3
    assert payload["model_id"] == result.model_id


def test_predict_rejects_bad_shapes(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)
    with pytest.raises(InvalidInputError):
        db.predict(result.model_id, X=[[0.0, 0.0, 0.0]])
    with pytest.raises(InvalidInputError):
        db.predict(result.model_id, X=[])


def test_predict_requires_a_model(db):
    with pytest.raises(InvalidInputError):
        db.predict(X=[[0.0, 0.0]])


def test_predict_rejects_both_model_and_model_id(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)
    with pytest.raises(InvalidInputError):
        db.predict(result.model_id, X=[[0.0, 0.0]], model=result.model)


# ── Error contract ───────────────────────────────────────────────────────────

def test_unknown_dataset_raises(db):
    with pytest.raises(UnknownDatasetError) as exc:
        db.train(dataset="does-not-exist")
    assert exc.value.code == "E2001_UNKNOWN_DATASET"
    assert isinstance(exc.value, MLDBError)


def test_unknown_model_raises(db):
    with pytest.raises(UnknownModelError) as exc:
        db.train(model="NoSuchModel", dataset="circles")
    assert exc.value.code == "E2002_UNKNOWN_MODEL"


def test_missing_model_id_raises(db):
    with pytest.raises(ModelNotFoundError) as exc:
        db.load_model("2020-01-01_deadbe")
    assert exc.value.code == "E2003_MODEL_NOT_FOUND"


def test_invalid_test_size_raises(db):
    with pytest.raises(InvalidInputError):
        db.train(dataset="circles", test_size=1.5)


# ── Registry passthrough ─────────────────────────────────────────────────────

def test_tag_and_untag(db):
    result = db.train(model="SVM", dataset="circles", n_samples=200)
    db.tag(result.model_id, "v12")
    assert "v12" in db.get_model(result.model_id)["tags"]
    db.untag(result.model_id, "v12")
    assert "v12" not in db.get_model(result.model_id)["tags"]


def test_compare_two_models(db):
    a = db.train(model="SVM", dataset="circles", n_samples=200)
    b = db.train(model="Tree", dataset="circles", n_samples=200)
    diff = db.compare(a.model_id, b.model_id)
    assert "model1" in diff and "model2" in diff
    assert isinstance(diff["differences"], list)


def test_train_result_to_dict_is_json_friendly(db):
    import json

    result = db.train(model="SVM", dataset="circles", n_samples=200)
    payload = result.to_dict()
    assert "model" not in payload
    json.dumps(payload)  # must not raise
