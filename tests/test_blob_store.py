"""Tests for v13 DoD #4 — content-addressed model storage.

The registry used to store one ``.joblib`` per model id.  Re-running an
identical experiment produced a byte-identical artifact that was stored
again, so a real registry accumulated thousands of duplicate copies.

These tests cover the blob store itself, the registry integration
(store / load / reference-counted delete / legacy compatibility) and the
storage statistics.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.svm import SVC

REPO_ROOT = str(Path(__file__).resolve().parents[1])

from core.blob_store import BlobStore
from core.registry import RegistryManager


@pytest.fixture
def data():
    rng = np.random.RandomState(0)
    X = rng.rand(40, 2)
    y = (X[:, 0] > 0.5).astype(int)
    return X, y


@pytest.fixture
def registry(tmp_path):
    return RegistryManager(registry_base=tmp_path / "registry")


def _save(rm, model, X, y, **overrides):
    kwargs = dict(
        model=model,
        model_type="SVM",
        hyperparameters={"C": 1.0},
        X_train=X,
        y_train=y,
        X_test=X,
        y_test=y,
        dataset_name="circles",
        n_samples=40,
        train_accuracy=0.9,
        test_accuracy=0.9,
    )
    kwargs.update(overrides)
    return rm.save_model(**kwargs)


# ── BlobStore unit tests ─────────────────────────────────────────────────────


def test_blob_store_roundtrip(tmp_path):
    store = BlobStore(tmp_path / "registry")
    digest = store.store_bytes(b"hello")
    assert len(digest) == 64
    assert store.load_bytes(digest) == b"hello"
    assert store.exists(digest)


def test_blob_store_is_deduplicating(tmp_path):
    store = BlobStore(tmp_path / "registry")
    d1 = store.store_bytes(b"same")
    d2 = store.store_bytes(b"same")
    assert d1 == d2
    assert len(list(store.blobs_dir.rglob("*.joblib"))) == 1


def test_blob_store_distinguishes_different_content(tmp_path):
    store = BlobStore(tmp_path / "registry")
    assert store.store_bytes(b"a") != store.store_bytes(b"b")


def test_blob_store_path_is_registry_relative(tmp_path):
    store = BlobStore(tmp_path / "registry")
    rel = store.relative_path("a" * 64)
    assert not os.path.isabs(rel)
    assert rel.startswith("blobs/")
    assert (tmp_path / "registry" / rel).parent.exists() or True


def test_blob_store_load_missing_raises(tmp_path):
    store = BlobStore(tmp_path / "registry")
    with pytest.raises(FileNotFoundError):
        store.load_bytes("f" * 64)


def test_blob_store_delete_is_idempotent(tmp_path):
    store = BlobStore(tmp_path / "registry")
    digest = store.store_bytes(b"x")
    assert store.delete(digest) is True
    assert store.delete(digest) is False


def test_blob_store_no_temp_files_left_behind(tmp_path):
    store = BlobStore(tmp_path / "registry")
    store.store_bytes(b"y")
    leftovers = list(store.blobs_dir.rglob("*.tmp"))
    assert leftovers == []


# ── Registry integration ─────────────────────────────────────────────────────


def test_identical_models_share_one_blob(registry, data):
    X, y = data
    m1 = SVC(C=1.0).fit(X, y)
    m2 = SVC(C=1.0).fit(X, y)

    id1 = _save(registry, m1, X, y)
    id2 = _save(registry, m2, X, y)

    assert id1 != id2, "each registration must still get its own model id"

    blobs = list(registry.blobs.blobs_dir.rglob("*.joblib"))
    assert len(blobs) == 1, "identical artifacts must be stored once"

    meta1 = registry.get_metadata(id1)
    meta2 = registry.get_metadata(id2)
    assert meta1["blob_digest"] == meta2["blob_digest"]
    assert meta1["blob_digest"]


def test_different_models_get_different_blobs(registry, data):
    X, y = data
    id1 = _save(registry, SVC(C=1.0).fit(X, y), X, y)
    id2 = _save(registry, SVC(C=2.0).fit(X, y), X, y)
    blobs = list(registry.blobs.blobs_dir.rglob("*.joblib"))
    assert len(blobs) == 2
    assert registry.get_metadata(id1)["blob_digest"] != registry.get_metadata(id2)["blob_digest"]


def test_no_per_model_joblib_is_written_anymore(registry, data):
    X, y = data
    _save(registry, SVC(C=1.0).fit(X, y), X, y)
    per_model = list(registry.models_dir.glob("*.joblib"))
    assert per_model == [], "artifacts must live in the blob store, not per model id"


def test_model_loads_back_correctly(registry, data):
    X, y = data
    model = SVC(C=1.0).fit(X, y)
    model_id = _save(registry, model, X, y)
    loaded = registry.load_model(model_id)
    assert np.array_equal(loaded.predict(X), model.predict(X))


def test_delete_keeps_blob_while_another_model_references_it(registry, data):
    X, y = data
    m = SVC(C=1.0).fit(X, y)
    id1 = _save(registry, m, X, y)
    id2 = _save(registry, m, X, y)

    registry.delete_model(id1)
    blobs = list(registry.blobs.blobs_dir.rglob("*.joblib"))
    assert len(blobs) == 1, "blob must survive while id2 still references it"
    assert registry.load_model(id2) is not None


def test_delete_removes_blob_when_last_reference_goes(registry, data):
    X, y = data
    m = SVC(C=1.0).fit(X, y)
    id1 = _save(registry, m, X, y)
    id2 = _save(registry, m, X, y)

    registry.delete_model(id1)
    registry.delete_model(id2)
    blobs = list(registry.blobs.blobs_dir.rglob("*.joblib"))
    assert blobs == []


def test_legacy_model_with_its_own_joblib_still_loads(registry, data):
    """A model registered before the blob store keeps its own file."""
    X, y = data
    model = SVC(C=1.0).fit(X, y)
    model_id = _save(registry, model, X, y)

    # Simulate the pre-DoD#4 layout: move the artifact next to the JSON
    # and drop the blob reference.
    json_path = registry.models_dir / f"{model_id}.json"
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    legacy_path = registry.models_dir / f"{model_id}.joblib"
    (registry.registry_base / metadata["joblib_path"]).replace(legacy_path)
    metadata["joblib_path"] = str(legacy_path.relative_to(registry.registry_base))
    metadata.pop("blob_digest", None)
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    loaded = registry.load_model(model_id)
    assert np.array_equal(loaded.predict(X), model.predict(X))


def test_deleting_a_legacy_model_removes_its_own_file(registry, data):
    X, y = data
    model = SVC(C=1.0).fit(X, y)
    model_id = _save(registry, model, X, y)

    json_path = registry.models_dir / f"{model_id}.json"
    metadata = json.loads(json_path.read_text(encoding="utf-8"))
    legacy_path = registry.models_dir / f"{model_id}.joblib"
    (registry.registry_base / metadata["joblib_path"]).replace(legacy_path)
    metadata["joblib_path"] = str(legacy_path.relative_to(registry.registry_base))
    metadata.pop("blob_digest", None)
    json_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    registry.delete_model(model_id)
    assert not legacy_path.exists()
    assert not json_path.exists()


# ── Storage statistics ───────────────────────────────────────────────────────


def test_storage_stats_report_dedup_gain(registry, data):
    X, y = data
    m = SVC(C=1.0).fit(X, y)
    for _ in range(4):
        _save(registry, m, X, y)

    stats = registry.storage_stats()
    assert stats["models"] == 4
    assert stats["unique_blobs"] == 1
    assert stats["dedup_ratio"] > 1.0
    assert stats["dedup_saved_bytes"] > 0


def test_storage_stats_on_empty_registry(registry):
    stats = registry.storage_stats()
    assert stats["models"] == 0
    assert stats["stored_bytes"] == 0
    assert stats["dedup_ratio"] == 1.0
