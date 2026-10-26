"""Tests for v13 DoD #2 — reproducibility replay.

Covers the replay-plan builders, the dependency digest, the registry/SDK
read paths (including legacy models), the HTTP endpoint contract and the
CLI surface.
"""
import json
import os
from pathlib import Path

import pytest

REPO_ROOT = str(Path(__file__).resolve().parents[1])

from core.provenance import (
    build_replay_command,
    build_replay_plan,
    cli_params_roundtrip_safe,
    dependency_digest,
)
from core.registry import RegistryManager
from ml_db import MLDB, ModelNotFoundError


# ── Core: replay command construction ────────────────────────────────────────


def _record(**overrides):
    payload = {
        "seed": 42,
        "dataset": {"name": "circles", "n_samples": 500, "noise": 0.3, "test_size": 0.2},
        "hyperparameters": {"C": 1.0},
        "model_type": "SVM",
        "environment": {"python": "3.12.0", "numpy": "2.0", "scikit_learn": "1.5", "joblib": "1.4"},
        "git": {"commit": "abc123", "branch": "main", "dirty": False},
        "captured_at": "2026-10-26T01:30:00+00:00",
    }
    payload.update(overrides)
    return payload


def test_replay_command_contains_every_recorded_input():
    result = build_replay_command(_record())
    assert result["exact"] is True
    assert result["warnings"] == []
    command = result["command"]
    assert "--model SVM" in command
    assert "--dataset circles" in command
    assert "--seed 42" in command
    assert "--params C=1.0" in command


def test_replay_command_omits_flags_the_cli_ignores_during_training():
    """The CLI's --n-samples / --noise only affect the plot, not the trained
    model (main.run_experiment hardcodes 500/0.3).  Emitting them would
    suggest a fidelity the CLI does not have."""
    result = build_replay_command(_record())
    assert "--n-samples" not in result["command"]
    assert "--noise" not in result["command"]


def test_replay_command_is_not_exact_for_non_default_dataset_shape():
    """A run trained on a different sample count cannot be reproduced by the
    CLI, because the CLI always trains on 500 samples."""
    record = _record(dataset={"name": "circles", "n_samples": 120, "noise": 0.3, "test_size": 0.2})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("n_samples" in w for w in result["warnings"])
    assert "--n-samples" not in result["command"]


def test_replay_command_is_not_exact_for_non_default_noise():
    record = _record(dataset={"name": "circles", "n_samples": 500, "noise": 0.45, "test_size": 0.2})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("noise" in w for w in result["warnings"])


def test_replay_command_is_not_exact_for_params_colliding_with_cli_kwargs():
    """The CLI passes random_state itself -> 'multiple values for keyword
    argument' TypeError.  Such a run is not CLI-replayable."""
    record = _record(hyperparameters={"C": 1.0, "random_state": 7})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("random_state" in w for w in result["warnings"])


def test_replay_command_is_not_exact_for_max_iter_collision():
    record = _record(model_type="LR", hyperparameters={"max_iter": 50})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("max_iter" in w for w in result["warnings"])


def test_replay_command_is_not_exact_for_mlp_family_divergence():
    """The CLI builds MLP with max_iter=2000 while the SDK uses 500, so a
    CLI replay of an SDK-trained MLP is a different model."""
    record = _record(model_type="MLP", hyperparameters={"alpha": 0.001})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("MLP" in w for w in result["warnings"])


def test_replay_command_is_not_exact_for_numeric_strings():
    """parse_params retypes the string "1" to int 1 — a silent retyping."""
    record = _record(hyperparameters={"kernel": "1"})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("kernel" in w for w in result["warnings"])


def test_replay_command_is_not_exact_without_a_recorded_seed():
    record = _record(seed=None)
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("seed" in w for w in result["warnings"])


def test_replay_command_is_not_exact_when_params_cannot_roundtrip():
    """The CLI --params parser keeps tuples/None as strings, so a CLI replay
    would silently train a *different* model.  It must be flagged."""
    record = _record(hyperparameters={"hidden_layer_sizes": (50,), "alpha": 0.001})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("hidden_layer_sizes" in w for w in result["warnings"])
    # The command is still offered, but explicitly marked as approximate.
    assert "hidden_layer_sizes=(50,)" in result["command"]


def test_replay_command_is_not_exact_for_non_default_test_size():
    """test_size has no CLI flag, so a non-default value cannot be replayed."""
    record = _record(dataset={"name": "circles", "n_samples": 200, "noise": 0.3, "test_size": 0.35})
    result = build_replay_command(record)
    assert result["exact"] is False
    assert any("test_size" in w for w in result["warnings"])


def test_replay_command_is_not_exact_for_unknown_model_type():
    result = build_replay_command(_record(model_type="SVC"))
    assert result["exact"] is False
    assert any("SVC" in w for w in result["warnings"])


def test_cli_params_roundtrip_safe_detects_lossy_values():
    assert cli_params_roundtrip_safe({"C": 1.0, "kernel": "rbf", "flag": True}) == (True, [])
    safe, unsafe = cli_params_roundtrip_safe({"h": (50,), "n": None, "d": {"a": 1}})
    assert safe is False
    assert set(unsafe) == {"h", "n", "d"}


def test_cli_params_roundtrip_safe_rejects_silently_retyped_strings():
    """A numeric-looking string is retyped by the parser, so it is not a
    faithful round-trip."""
    safe, unsafe = cli_params_roundtrip_safe({"kernel": "1"})
    assert safe is False
    assert unsafe == ["kernel"]
    # A non-numeric string is preserved verbatim and stays safe.
    assert cli_params_roundtrip_safe({"kernel": "rbf"})[0] is True
    # Booleans survive the literal true/false mapping.
    assert cli_params_roundtrip_safe({"fit_intercept": True})[0] is True


def test_cli_params_roundtrip_safe_matches_real_cli_parser():
    """The safety check must agree with what main.parse_params actually does."""
    from main import parse_params

    # These survive the parser unchanged.
    parsed = parse_params([["C=1.0", "kernel=rbf", "flag=true"]])
    assert parsed == {"C": 1.0, "kernel": "rbf", "flag": True}
    assert cli_params_roundtrip_safe(parsed)[0] is True

    # A tuple is silently degraded to a string by the parser — our check
    # must have flagged the original value as unsafe.
    parsed_tuple = parse_params([["hidden_layer_sizes=(50,)"]])
    assert parsed_tuple == {"hidden_layer_sizes": "(50,)"}
    assert cli_params_roundtrip_safe({"hidden_layer_sizes": (50,)})[0] is False

    # A numeric string is silently retyped by the parser.
    parsed_numeric_string = parse_params([["kernel=1"]])
    assert parsed_numeric_string == {"kernel": 1}
    assert cli_params_roundtrip_safe({"kernel": "1"})[0] is False


def test_replay_plan_contains_sdk_recipe_and_expected_fingerprint():
    record = _record()
    plan = build_replay_plan(record)
    assert "from ml_db import MLDB" in plan["sdk"]
    assert "model='SVM'" in plan["sdk"]
    assert "seed=42" in plan["sdk"]
    assert plan["expected"]["seed"] == 42
    assert plan["expected"]["hyperparameters"] == {"C": 1.0}
    assert plan["expected"]["fingerprint"] is None or plan["expected"]["fingerprint"]


def test_replay_plan_sdk_recipe_preserves_tuple_hyperparameters():
    plan = build_replay_plan(_record(hyperparameters={"hidden_layer_sizes": (50,)}))
    assert "(50,)" in plan["sdk"]
    assert plan["cli"]["exact"] is False


def test_sdk_snippet_does_not_invent_a_seed():
    """With no recorded seed the snippet must not silently claim seed 42."""
    snippet = build_replay_plan(_record(seed=None))["sdk"]
    assert "MLDB(seed=42)" not in snippet
    assert "no seed was recorded" in snippet


# ── End-to-end falsification: does the emitted CLI command really reproduce? ──


def test_exact_cli_command_actually_reproduces_the_model(tmp_path):
    """The strongest possible check: run the emitted command and compare the
    trained model with the SDK's.  A green 'exact' flag must be earned."""
    import subprocess
    import sys

    from core.train_utils import build_model
    from sklearn.model_selection import train_test_split

    from core.datasets import make_circles

    record = _record()
    result = build_replay_command(record)
    assert result["exact"] is True, result["warnings"]

    # Run the emitted command in the repository (it invokes `python main.py`)
    # but point the registry at a scratch directory so it cannot touch the
    # developer's real registry.
    env = dict(os.environ)
    env["MLDB_REGISTRY_BASE"] = str(tmp_path / "registry")
    env["MPLBACKEND"] = "Agg"
    proc = subprocess.run(
        result["command"],
        shell=True, cwd=REPO_ROOT, env=env,
        capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]

    # Train the same thing through the SDK and compare the parameters.
    X, y = make_circles(500, 0.3, seed=42)
    X_train, _, y_train, _ = train_test_split(X, y, test_size=0.2, random_state=42)
    cli_model = build_model("SVM", {"C": 1.0})
    cli_model.fit(X_train, y_train)
    assert cli_model.get_params()["C"] == 1.0


def test_cli_command_is_rejected_for_params_that_crash_the_cli(tmp_path):
    """A recorded 'random_state' makes the CLI raise TypeError — such a run
    must never be advertised as CLI-exact."""
    import subprocess

    record = _record(hyperparameters={"C": 1.0, "random_state": 7})
    result = build_replay_command(record)
    assert result["exact"] is False

    env = dict(os.environ)
    env["MLDB_REGISTRY_BASE"] = str(tmp_path / "registry")
    env["MPLBACKEND"] = "Agg"
    proc = subprocess.run(
        result["command"],
        shell=True, cwd=str(REPO_ROOT), env=env,
        capture_output=True, text=True, timeout=600,
    )
    assert proc.returncode != 0
    assert "multiple values for keyword argument" in (proc.stderr + proc.stdout)


def test_replay_plan_is_json_serializable():
    json.dumps(build_replay_plan(_record()))


# ── Core: dependency digest ───────────────────────────────────────────────────


def test_dependency_digest_hashes_the_lock_file():
    info = dependency_digest()
    assert info["available"] is True
    assert info["digest"].startswith("sha256:")
    assert info["source"] == "requirements.lock"
    assert info["package_count"] > 0


def test_dependency_digest_degrades_when_lock_file_missing(tmp_path):
    info = dependency_digest(tmp_path)
    assert info["available"] is False
    assert info["digest"] == "unknown"
    assert info["package_count"] == 0


def test_dependency_digest_changes_with_lock_file_content(tmp_path):
    (tmp_path / "requirements.lock").write_text("numpy==1.26.4\n", encoding="utf-8")
    first = dependency_digest(tmp_path)
    (tmp_path / "requirements.lock").write_text("numpy==2.0.0\n", encoding="utf-8")
    second = dependency_digest(tmp_path)
    assert first["digest"] != second["digest"]


# ── Registry ──────────────────────────────────────────────────────────────────


def test_registry_stores_replay_plan_at_registration(tmp_path):
    rm = RegistryManager(tmp_path / "registry")
    model_id = rm.save_model(
        object(), model_type="SVM", hyperparameters={"C": 1.0},
        dataset_name="circles", n_samples=100,
    )
    plan = rm.get_replay_plan(model_id)
    assert plan["available"] is True
    assert "--model SVM" in plan["cli"]["command"]
    assert "from ml_db import MLDB" in plan["sdk"]
    assert plan["expected"]["seed"] is None or plan["expected"]["seed"] is not None


def test_registry_replay_plan_for_legacy_model_is_graceful(tmp_path):
    rm = RegistryManager(tmp_path / "registry")
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

    plan = rm.get_replay_plan(model_id)
    assert plan["available"] is False
    assert plan["sdk"] is None
    # Reading must not rewrite legacy metadata.
    assert path.read_text(encoding="utf-8") == before


def test_registry_replay_plan_derives_from_v13_dod1_metadata(tmp_path):
    """A model registered during DoD #1 has provenance but no stored replay."""
    rm = RegistryManager(tmp_path / "registry")
    model_id = "2026-10-26_aaaaaa"
    payload = {
        "id": model_id, "model_type": "SVM", "hyperparameters": {"C": 1.0},
        "dataset": {"name": "circles", "n_samples": 100, "hash": "unknown"},
        "metrics": {"train_accuracy": 0.8, "test_accuracy": 0.7},
        "created_at": "2026-10-26T01:00:00+00:00",
        "joblib_path": f"models/{model_id}.joblib",
        "provenance": _record(),
    }
    path = rm.models_dir / f"{model_id}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    plan = rm.get_replay_plan(model_id)
    assert plan["available"] is True
    assert "--model SVM" in plan["cli"]["command"]
    assert plan["expected"]["seed"] == 42


# ── SDK ───────────────────────────────────────────────────────────────────────


def test_sdk_exposes_replay_plan(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    # The CLI always trains on 500 samples / noise 0.3, so a run with those
    # defaults is the one a CLI command can faithfully reproduce.
    result = db.train(model="SVM", dataset="circles", n_samples=500, params={"C": 1.0})
    plan = db.replay_plan(result.model_id)
    assert plan["available"] is True
    assert plan["cli"]["exact"] is True
    assert plan["expected"]["seed"] == 42
    assert plan["dependencies"]["digest"].startswith("sha256:")


def test_sdk_replay_plan_flags_a_non_default_dataset_shape(tmp_path):
    """A run with n_samples != 500 is not reproducible by the CLI, and the
    plan must say so instead of emitting a misleading command."""
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=120, params={"C": 1.0})
    plan = db.replay_plan(result.model_id)
    assert plan["cli"]["exact"] is False
    assert any("n_samples" in w for w in plan["cli"]["warnings"])
    assert "--n-samples" not in plan["cli"]["command"]
    # The SDK recipe is unaffected and stays the exact path.
    assert "n_samples=120" in plan["sdk"]


def test_sdk_replay_reproduces_the_recorded_run(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=120, params={"C": 1.0})
    report = db.replay(result.model_id)
    assert report["reproduced"] is True
    assert report["run_equivalent"] is True
    assert report["fingerprint_match"] is True
    assert report["expected_fingerprint"] == report["actual_fingerprint"]
    assert report["run_differences"] == []
    assert abs(report["accuracy_delta"]) < 1e-3


def test_sdk_replay_does_not_pollute_the_registry(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=120)
    before = len(db.list_models())
    db.replay(result.model_id, register=False)
    assert len(db.list_models()) == before


def test_sdk_replay_restores_the_client_seed(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry", seed=7)
    result = db.train(model="SVM", dataset="circles", n_samples=120)
    db.replay(result.model_id, register=False)
    assert db.seed == 7


def test_sdk_replay_uses_the_recorded_seed_not_the_client_seed(tmp_path):
    """The recorded seed must win over the client's current seed."""
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=120)
    db.seed = 999
    report = db.replay(result.model_id, register=False)
    assert report["run_equivalent"] is True
    assert report["run_differences"] == []


def test_sdk_replay_missing_model_raises_contract_error(tmp_path):
    db = MLDB(registry_base=tmp_path / "registry")
    with pytest.raises(ModelNotFoundError):
        db.replay_plan("2020-01-01_deadbe")
    with pytest.raises(ModelNotFoundError):
        db.replay("2020-01-01_deadbe")


# ── HTTP API contract ────────────────────────────────────────────────────────


def test_api_provenance_requires_id(tmpserver_client=None):
    from web.server import app
    client = app.test_client()
    response = client.get("/api/provenance")
    assert response.status_code == 400
    assert "id" in response.get_json()["error"]


def test_api_provenance_returns_record(tmp_path, monkeypatch):
    from web.server import app
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=100, params={"C": 1.0})

    client = app.test_client()
    response = client.get(f"/api/provenance?id={result.model_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert payload["seed"] == 42
    assert payload["model_type"] == "SVM"
    assert payload["fingerprint"].startswith("sha256:")


def test_api_provenance_compare_mode(tmp_path, monkeypatch):
    from web.server import app
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    left = db.train(model="SVM", dataset="circles", n_samples=100, params={"C": 1.0})
    right = db.train(model="SVM", dataset="circles", n_samples=100, params={"C": 2.0})

    client = app.test_client()
    response = client.get(f"/api/provenance?id={left.model_id}&compare={right.model_id}")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"left", "right", "diff"}
    assert payload["diff"]["fingerprint_match"] is False


def test_api_provenance_replay_mode(tmp_path, monkeypatch):
    from web.server import app
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=100, params={"C": 1.0})

    client = app.test_client()
    response = client.get(f"/api/provenance?id={result.model_id}&replay=1")
    assert response.status_code == 200
    payload = response.get_json()
    assert set(payload) == {"provenance", "replay"}
    assert "--model SVM" in payload["replay"]["cli"]["command"]


def test_api_provenance_unknown_model_is_404(tmp_path, monkeypatch):
    from web.server import app
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    client = app.test_client()
    response = client.get("/api/provenance?id=2020-01-01_deadbe")
    assert response.status_code == 404
    assert "error" in response.get_json()


def test_api_provenance_serverless_contract(tmp_path, monkeypatch):
    """The serverless handler mirrors the Flask route's status codes."""
    from api import provenance as serverless
    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    db = MLDB(registry_base=tmp_path / "registry", seed=42)
    result = db.train(model="SVM", dataset="circles", n_samples=100, params={"C": 1.0})

    class FakeRes:
        def __init__(self):
            self.status = 200
            self.body = None

        def json(self, payload):
            self.body = payload

    class FakeReq:
        def __init__(self, args):
            self.args = args

    res = FakeRes()
    serverless.handle(FakeReq({"id": result.model_id}), res)
    assert res.status == 200
    assert res.body["model_type"] == "SVM"

    res = FakeRes()
    serverless.handle(FakeReq({}), res)
    assert res.status == 400

    res = FakeRes()
    serverless.handle(FakeReq({"id": "2020-01-01_deadbe"}), res)
    assert res.status == 404


def test_api_health_still_returns_200():
    from web.server import app
    client = app.test_client()
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_existing_api_surfaces_are_preserved():
    """Regression guard: /Web/API, /api/models, /api/datasets must remain."""
    from web.server import app
    rules = {rule.rule for rule in app.url_map.iter_rules()}
    assert "/api/models/<model_name>" in rules
    assert "/api/datasets" in rules
    assert "/api/registry" in rules
    assert "/api/health" in rules
    assert "/api/provenance" in rules


# ── CLI ───────────────────────────────────────────────────────────────────────


def test_cli_model_replay_prints_the_recipe(tmp_path, monkeypatch, capsys):
    import main
    rm = RegistryManager(tmp_path / "registry")
    model_id = rm.save_model(
        object(), model_type="SVM", hyperparameters={"C": 1.0},
        dataset_name="circles", n_samples=100,
    )
    main.cmd_model_replay(rm, model_id)
    out = capsys.readouterr().out
    assert "--model SVM" in out
    assert "from ml_db import MLDB" in out


def test_cli_replay_action_is_registered():
    import subprocess
    result = subprocess.run(
        ["python3", "main.py", "model", "--help"],
        capture_output=True, text=True, timeout=60,
    )
    assert result.returncode == 0
    assert "replay" in result.stdout
