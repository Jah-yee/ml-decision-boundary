"""Integration tests for the replay integrity guard (v13 DoD #4).

These cover the surfaces the guard is wired into: the registry, the SDK, the
CLI and both HTTP entry points.  The guard is the same core logic on every
surface, so the tests assert that they agree.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

from core.registry import RegistryManager
from ml_db.client import MLDB
from ml_db.errors import ModelNotFoundError

REPO_ROOT = Path(__file__).resolve().parents[1]


# ── Fixtures / helpers ──────────────────────────────────────────────────────

@pytest.fixture
def registry(tmp_path):
    return RegistryManager(registry_base=tmp_path / "registry")


def _register(registry, model_type="SVM", params=None, dataset="circles"):
    """Register a model that carries full v13 provenance.

    Returns the new model's id.
    """
    return registry.save_model(
        model=None,
        model_type=model_type,
        hyperparameters=params or {"C": 1.0},
        dataset_name=dataset,
        n_samples=400,
        train_accuracy=0.8,
        test_accuracy=0.79,
    )


def _run_cli(args, registry_dir):
    return subprocess.run(
        [sys.executable, "main.py"] + args,
        cwd=REPO_ROOT,
        env={**os.environ, "MLDB_REGISTRY_BASE": str(registry_dir)},
        capture_output=True,
        text=True,
        timeout=300,
    )


# ── Registry ────────────────────────────────────────────────────────────────

def test_registry_replay_integrity_on_empty_registry(registry):
    report = registry.replay_integrity()
    assert report["total"] == 0
    assert report["stale"] == 0
    assert report["broken"] == 0
    assert report["models"] == []


def test_registry_replay_integrity_counts_a_fresh_model_as_current(registry):
    _register(registry)
    report = registry.replay_integrity()
    assert report["total"] == 1
    assert report["with_provenance"] == 1
    assert report["by_drift"]["none"] == 1
    assert report["stale"] == 0


def test_registry_replay_integrity_flags_a_semantically_drifted_model(registry):
    model_id = _register(registry)

    # Rewrite the frozen recipe so it describes a different run.
    path = registry.models_dir / f"{model_id}.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["provenance"]["replay"]["cli"]["command"] = (
        "python main.py --model SVM --dataset moons --seed 42 --params C=1.0"
    )
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    report = registry.replay_integrity()
    assert report["by_drift"]["semantic"] == 1
    assert report["broken"] == 1
    assert [m["model_id"] for m in report["models"]] == [model_id]
    assert "--dataset" in report["models"][0]["changed_fields"]


def test_registry_recipe_drift_for_a_single_model(registry):
    model_id = _register(registry)
    verdict = registry.recipe_drift(model_id)
    assert verdict["model_id"] == model_id
    assert verdict["drift"] == "none"
    assert verdict["reproduces_same_model"] is True


def test_registry_recipe_drift_raises_for_an_unknown_model(registry):
    with pytest.raises(FileNotFoundError):
        registry.recipe_drift("nope-not-here")


def test_registry_replay_integrity_does_not_rewrite_metadata(registry):
    model_id = _register(registry)
    path = registry.models_dir / f"{model_id}.json"
    before = path.read_text(encoding="utf-8")
    registry.replay_integrity()
    after = path.read_text(encoding="utf-8")
    assert before == after


# ── SDK ─────────────────────────────────────────────────────────────────────

def test_sdk_replay_integrity_matches_the_registry(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    db.train(model="SVM", dataset="circles", params={"C": 1.0}, register=True)

    report = db.replay_integrity()
    assert report["total"] == 1
    assert report["by_drift"]["none"] == 1
    assert report["broken"] == 0


def test_sdk_recipe_drift_returns_a_verdict(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    result = db.train(model="SVM", dataset="circles", params={"C": 1.0}, register=True)
    verdict = db.recipe_drift(result.model_id)
    assert verdict["drift"] == "none"
    assert verdict["model_id"] == result.model_id


def test_sdk_recipe_drift_raises_for_an_unknown_model(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    with pytest.raises(ModelNotFoundError):
        db.recipe_drift("nope-not-here")


def test_sdk_verify_replay_executes_the_replay(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    result = db.train(model="SVM", dataset="circles", params={"C": 1.0}, register=True)

    verified = db.verify_replay(result.model_id)
    assert verified["verified"] is True
    assert verified["status"] in ("reproduced", "drifted")
    assert verified["accuracy"] is not None
    assert "drift" in verified


def test_sdk_verify_replay_raises_for_an_unknown_model(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    with pytest.raises(ModelNotFoundError):
        db.verify_replay("nope-not-here")


def test_sdk_verify_replay_does_not_register_a_new_model(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    result = db.train(model="SVM", dataset="circles", params={"C": 1.0}, register=True)
    before = len(db.registry.list_models())
    db.verify_replay(result.model_id)
    after = len(db.registry.list_models())
    assert before == after


# ── CLI ─────────────────────────────────────────────────────────────────────

def test_cli_integrity_action_runs_on_an_empty_registry(tmp_path):
    result = _run_cli(["model", "integrity"], tmp_path / "registry")
    assert result.returncode == 0
    assert "No models registered yet" in result.stdout


def test_cli_integrity_action_reports_the_audit(tmp_path):
    registry_dir = tmp_path / "registry"
    rm = RegistryManager(registry_base=registry_dir)
    _register(rm)

    result = _run_cli(["model", "integrity"], registry_dir)
    assert result.returncode == 0
    assert "Replay integrity" in result.stdout
    assert "Recipe current" in result.stdout
    assert "Semantic drift" in result.stdout


def test_cli_integrity_action_lists_semantically_drifted_models(tmp_path):
    registry_dir = tmp_path / "registry"
    rm = RegistryManager(registry_base=registry_dir)
    model_id = _register(rm)

    path = rm.models_dir / f"{model_id}.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["provenance"]["replay"]["cli"]["command"] = (
        "python main.py --model SVM --dataset moons --seed 42 --params C=1.0"
    )
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    result = _run_cli(["model", "integrity"], registry_dir)
    assert result.returncode == 0
    assert "would NOT reproduce" in result.stdout
    assert model_id in result.stdout


def test_cli_verify_action_runs(tmp_path):
    registry_dir = tmp_path / "registry"
    rm = RegistryManager(registry_base=registry_dir)
    model_id = _register(rm)

    result = _run_cli(["model", "verify", model_id], registry_dir)
    assert result.returncode == 0
    assert "Replay verification" in result.stdout


def test_cli_verify_action_requires_a_model_id(tmp_path):
    result = _run_cli(["model", "verify"], tmp_path / "registry")
    assert result.returncode != 0
    assert "requires a model_id" in result.stdout


# ── HTTP contract ───────────────────────────────────────────────────────────

def test_api_provenance_integrity_mode_via_flask_test_client(tmp_path, monkeypatch):
    from web.server import app

    rm = RegistryManager(registry_base=tmp_path / "registry")
    _register(rm)
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/api/provenance?integrity=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["total"] == 1
    assert payload["by_drift"]["none"] == 1
    assert payload["broken"] == 0


def test_api_provenance_integrity_mode_via_serverless_handler(tmp_path, monkeypatch):
    import api.provenance as api_provenance

    rm = RegistryManager(registry_base=tmp_path / "registry")
    _register(rm)
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    class _Req:
        args = {"integrity": "1"}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    assert res.status == 200
    assert res.payload["total"] == 1


def test_api_provenance_integrity_for_a_single_model(tmp_path, monkeypatch):
    import api.provenance as api_provenance

    rm = RegistryManager(registry_base=tmp_path / "registry")
    model_id = _register(rm)
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    class _Req:
        args = {"integrity": "1", "id": model_id}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    assert res.status == 200
    assert res.payload["model_id"] == model_id
    assert res.payload["drift"] == "none"


def test_api_provenance_integrity_404s_for_an_unknown_model(tmp_path, monkeypatch):
    import api.provenance as api_provenance

    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    class _Req:
        args = {"integrity": "1", "id": "nope-not-here"}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    assert res.status == 404


def test_api_provenance_verify_mode_via_serverless_handler(tmp_path, monkeypatch):
    import api.provenance as api_provenance

    rm = RegistryManager(registry_base=tmp_path / "registry")
    model_id = _register(rm)
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    class _Req:
        args = {"verify": "1", "id": model_id}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    assert res.status == 200
    assert res.payload["model_id"] == model_id
    assert "status" in res.payload


def test_api_provenance_still_requires_id_without_integrity(tmp_path, monkeypatch):
    import api.provenance as api_provenance

    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))

    class _Req:
        args = {}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    assert res.status == 400


# ── Cross-surface agreement ─────────────────────────────────────────────────

def test_all_surfaces_agree_on_the_drift_verdict(tmp_path):
    """Registry, SDK and HTTP must not drift apart from each other."""
    registry_dir = tmp_path / "registry"
    rm = RegistryManager(registry_base=registry_dir)
    model_id = _register(rm)

    path = rm.models_dir / f"{model_id}.json"
    metadata = json.loads(path.read_text(encoding="utf-8"))
    metadata["provenance"]["replay"]["cli"]["command"] = (
        "python main.py --model SVM --dataset moons --seed 42 --params C=1.0"
    )
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    from_registry = rm.recipe_drift(model_id)["drift"]
    from_sdk = MLDB(registry_base=str(registry_dir)).recipe_drift(model_id)["drift"]

    import api.provenance as api_provenance

    os.environ["MLDB_REGISTRY_BASE"] = str(registry_dir)

    class _Req:
        args = {"integrity": "1", "id": model_id}

    class _Res:
        status = 200

        def json(self, payload):
            self.payload = payload

    res = _Res()
    api_provenance.handle(_Req(), res)
    from_api = res.payload["drift"]

    assert from_registry == from_sdk == from_api == "semantic"
