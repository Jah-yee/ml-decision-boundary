"""Tests for v13 DoD #1 — experiment provenance capture."""
import json

import pytest

from core.provenance import (
    build_provenance,
    canonical_json,
    compute_fingerprint,
    environment_info,
    git_info,
    provenance_diff,
)
from core.registry import RegistryManager
from ml_db import MLDB, ModelNotFoundError


def _record(**overrides):
    payload = {
        "seed": 42,
        "dataset": {"name": "circles", "n_samples": 200, "noise": 0.3, "test_size": 0.2},
        "hyperparameters": {"C": 1.0},
        "model_type": "SVM",
        "environment": {"python": "3.12.0", "numpy": "2.0", "scikit_learn": "1.5", "joblib": "1.4"},
        "git": {"commit": "abc123", "branch": "main", "dirty": False},
        "captured_at": "2026-10-26T01:30:00+00:00",
    }
    payload.update(overrides)
    payload["fingerprint"] = compute_fingerprint(payload)
    return payload


def test_canonical_json_is_stable_and_sorted():
    assert canonical_json({"b": 2, "a": 1}) == '{"a":1,"b":2}'


def test_build_provenance_has_complete_record():
    record = build_provenance(
        seed=7, dataset_name="moons", n_samples=120, noise=0.1,
        test_size=0.25, hyperparameters={"C": 2.0}, model_type="SVM",
        include_environment=False, include_git=False,
    )
    assert record["seed"] == 7
    assert record["dataset"] == {"name": "moons", "n_samples": 120, "noise": 0.1, "test_size": 0.25}
    assert record["hyperparameters"] == {"C": 2.0}
    assert record["model_type"] == "SVM"
    assert record["environment"] == {}
    assert record["git"]["commit"] == "unknown"
    assert record["fingerprint"].startswith("sha256:")
    json.dumps(record)


def test_fingerprint_ignores_capture_time_and_dirty_state():
    left = _record()
    right = _record(captured_at="2027-01-01T00:00:00+00:00", git={"commit": "abc123", "branch": "other", "dirty": True})
    assert compute_fingerprint(left) == compute_fingerprint(right)
    assert provenance_diff(left, right)["identical"] is True


def test_fingerprint_changes_with_reproducibility_fields():
    diff = provenance_diff(_record(), _record(seed=43))
    assert diff["fingerprint_match"] is False
    assert {"field": "seed", "left": 42, "right": 43} in diff["differences"]


def test_provenance_diff_returns_structured_values():
    diff = provenance_diff(_record(), _record(model_type="RF"))
    assert diff["identical"] is False
    assert diff["differences"] == [{"field": "model_type", "left": "SVM", "right": "RF"}]


def test_environment_info_contains_expected_versions():
    env = environment_info()
    assert env["python"] and env["implementation"]
    assert "numpy" in env and "scikit_learn" in env and "joblib" in env


def test_git_info_never_raises_for_non_repo(tmp_path):
    info = git_info(tmp_path)
    assert info["commit"] == "unknown"
    assert info["branch"] == "unknown"
    assert info["dirty"] is False


def test_registry_saves_and_reads_provenance(tmp_path):
    rm = RegistryManager(tmp_path / "registry")
    model_id = rm.save_model(
        object(), model_type="SVM", hyperparameters={"C": 1.0},
        dataset_name="circles", n_samples=100, provenance=_record(),
    )
    stored = rm.get_provenance(model_id)
    assert stored["seed"] == 42
    assert stored["fingerprint"] == _record()["fingerprint"]


def test_registry_legacy_metadata_is_not_rewritten(tmp_path):
    rm = RegistryManager(tmp_path / "registry")
    rm._ensure_dirs()
    model_id = "2020-01-01_abcdef"
    payload = {
        "id": model_id, "model_type": "SVM", "hyperparameters": {},
        "dataset": {"name": "circles"},
        "metrics": {"train_accuracy": 0.8, "test_accuracy": 0.7},
        "created_at": "2020-01-01T00:00:00+00:00",
        "joblib_path": f"models/{model_id}.joblib",
    }
    path = rm.models_dir / f"{model_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    before = path.read_text(encoding="utf-8")
    assert rm.get_provenance(model_id) == {}
    assert path.read_text(encoding="utf-8") == before


def test_sdk_exposes_provenance_and_compare(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=120, params={"C": 1.0})
    record = db.get_provenance(result.model_id)
    assert record["seed"] == 42
    assert record["dataset"]["name"] == "circles"
    assert record["hyperparameters"] == {"C": 1.0}
    assert record["fingerprint"].startswith("sha256:")
    diff = db.compare_provenance(result.model_id, result.model_id)
    assert diff["identical"] is True
    assert diff["fingerprint_match"] is True
    assert diff["differences"] == []


def test_sdk_missing_model_raises_contract_error(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry")
    with pytest.raises(ModelNotFoundError):
        db.get_provenance("2020-01-01_deadbe")
    with pytest.raises(ModelNotFoundError):
        db.compare_provenance("2020-01-01_deadbe", "2020-01-01_beefed")
