"""Tests for v13 DoD #3 — provenance coverage audit + replay execution.

Covers the coverage classifier, the summary/replayability aggregators, the
registry/SDK read paths (including legacy models), the CLI surface and the
HTTP endpoint contract.
"""
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = str(Path(__file__).resolve().parents[1])

from core.coverage import (
    COVERAGE_STATUSES,
    classify_model,
    cli_replay_check,
    coverage_summary,
    provenance_coverage,
    replayability_report,
)
from core.registry import RegistryManager
from ml_db import MLDB


# ── Fixtures: synthetic registry records ─────────────────────────────────────


def _legacy_model(model_id="legacy-1"):
    """A model registered before v13: no provenance at all."""
    return {
        "id": model_id,
        "model_type": "SVM",
        "hyperparameters": {"C": 1.0},
        "dataset": {"name": "circles", "n_samples": 400, "hash": "sha256:abc"},
        "metrics": {"train_accuracy": 0.5, "test_accuracy": 0.43},
        "created_at": "2026-09-18T13:52:45.651358+00:00",
        "accuracy": 0.43,
        "tags": [],
        "version": 1,
        "family": "SVM|circles",
    }


def _model_with_provenance(model_id="prov-1", seed=42, params=None, replay=True, cli_exact=True):
    """A model with a provenance record (optionally with a frozen replay plan)."""
    provenance = {
        "seed": seed,
        "dataset": {"name": "circles", "n_samples": 500, "noise": 0.3, "test_size": 0.2},
        "hyperparameters": params if params is not None else {"C": 1.0},
        "model_type": "SVM",
        "environment": {"python": "3.12.0", "numpy": "2.0", "scikit_learn": "1.5", "joblib": "1.4"},
        "git": {"commit": "abc123", "branch": "main", "dirty": False},
        "captured_at": "2026-10-26T01:30:00+00:00",
        "fingerprint": "sha256:deadbeefdeadbeef",
    }
    if replay:
        provenance["replay"] = {
            "sdk": "from ml_db import MLDB\ndb = MLDB(seed=42)",
            "cli": {"command": "python main.py --model SVM", "exact": cli_exact, "warnings": [] if cli_exact else ["lossy"]},
            "dependencies": {"available": True, "digest": "sha256:abc", "package_count": 10},
            "expected": {"fingerprint": "sha256:deadbeefdeadbeef"},
        }
    return {
        "id": model_id,
        "model_type": "SVM",
        "hyperparameters": params if params is not None else {"C": 1.0},
        "dataset": {"name": "circles", "n_samples": 500, "hash": "sha256:abc"},
        "metrics": {"train_accuracy": 0.8, "test_accuracy": 0.79},
        "created_at": "2026-10-26T01:30:00+00:00",
        "accuracy": 0.79,
        "tags": [],
        "version": 1,
        "family": "SVM|circles",
        "provenance": provenance,
    }


# ── Core: classification ─────────────────────────────────────────────────────


def test_legacy_model_is_classified_as_no_provenance():
    result = classify_model(_legacy_model())
    assert result["status"] == "no_provenance"
    assert result["provenance"] is False
    assert result["replay"] is False
    assert result["cli_exact"] is False
    assert "before v13" in result["reason"]


def test_model_with_frozen_replay_is_replayable_exact():
    result = classify_model(_model_with_provenance())
    assert result["status"] == "replayable_exact"
    assert result["provenance"] is True
    assert result["replay"] is True
    assert result["cli_exact"] is True
    assert result["fingerprint"] == "sha256:deadbeefdeadbeef"
    assert result["reason"] == ""


def test_model_with_lossy_cli_falls_back_to_sdk_status():
    result = classify_model(_model_with_provenance(cli_exact=False))
    assert result["status"] == "replayable_sdk"
    assert result["replay"] is True
    assert result["cli_exact"] is False
    assert result["reason"] == "lossy"


def test_provenance_without_replay_plan_is_provenance_only():
    result = classify_model(_model_with_provenance(replay=False))
    assert result["status"] == "provenance_only"
    assert result["provenance"] is True
    assert result["replay"] is False


def test_classification_uses_caller_supplied_replay_plan():
    """A DoD #1 model has no frozen snapshot but its plan is derivable."""
    model = _model_with_provenance(replay=False)
    derived = {"sdk": "from ml_db import MLDB", "cli": {"command": "x", "exact": True, "warnings": []}}
    result = classify_model(model, derived)
    assert result["status"] == "replayable_exact"
    assert result["replay"] is True


def test_every_status_is_one_of_the_declared_states():
    for model in (
        _legacy_model(),
        _model_with_provenance(),
        _model_with_provenance(cli_exact=False),
        _model_with_provenance(replay=False),
    ):
        assert classify_model(model)["status"] in COVERAGE_STATUSES


def test_empty_model_dict_does_not_crash():
    result = classify_model({})
    assert result["status"] == "no_provenance"
    assert result["model_id"] == ""


# ── Core: summary aggregation ────────────────────────────────────────────────


def test_summary_counts_each_status():
    models = [
        _legacy_model("l1"),
        _legacy_model("l2"),
        _model_with_provenance("p1"),
        _model_with_provenance("p2", cli_exact=False),
        _model_with_provenance("p3", replay=False),
    ]
    summary = coverage_summary(models)
    assert summary["total"] == 5
    assert summary["with_provenance"] == 3
    assert summary["with_replay"] == 2
    assert summary["cli_exact"] == 1
    assert summary["reproducible"] == 2
    assert summary["by_status"] == {
        "replayable_exact": 1,
        "replayable_sdk": 1,
        "provenance_only": 1,
        "no_provenance": 2,
    }


def test_summary_percentages_are_rounded():
    models = [_model_with_provenance()] + [_legacy_model() for _ in range(3)]
    summary = coverage_summary(models)
    assert summary["coverage_pct"] == 25.0
    assert summary["replayable_pct"] == 25.0
    assert summary["cli_exact_pct"] == 25.0


def test_summary_of_empty_registry_is_all_zero():
    summary = coverage_summary([])
    assert summary["total"] == 0
    assert summary["coverage_pct"] == 0.0
    assert summary["by_status"]["no_provenance"] == 0


def test_summary_respects_caller_supplied_replay_plans():
    models = [_model_with_provenance("p1", replay=False)]
    plans = {"p1": {"sdk": "x", "cli": {"command": "c", "exact": True, "warnings": []}}}
    summary = coverage_summary(models, plans)
    assert summary["with_replay"] == 1
    assert summary["reproducible"] == 1


# ── Core: replayability report ───────────────────────────────────────────────


def test_report_groups_blocked_models_by_cause():
    models = [
        _legacy_model("l1"),
        _legacy_model("l2"),
        _model_with_provenance("p1", cli_exact=False),
        _model_with_provenance("p2"),
    ]
    report = replayability_report(models)
    assert report["total"] == 4
    # A model with a lossy CLI command is still reproducible via the SDK
    # recipe, so it counts as reproducible.
    assert report["reproducible"] == 2
    assert report["blocked"] == 2
    causes = {item["reason"]: item["count"] for item in report["reasons"]}
    assert causes["registered before v13 — no provenance record"] == 2
    assert "lossy" not in causes


def test_report_lists_model_ids_per_cause():
    models = [_legacy_model("l1"), _legacy_model("l2")]
    report = replayability_report(models)
    assert len(report["reasons"]) == 1
    assert sorted(report["reasons"][0]["models"]) == ["l1", "l2"]


def test_report_is_empty_when_everything_is_replayable():
    report = replayability_report([_model_with_provenance()])
    assert report["blocked"] == 0
    assert report["reasons"] == []


# ── Core: CLI replay drift check ─────────────────────────────────────────────


def test_cli_replay_check_reports_no_drift_when_snapshot_matches():
    from core.provenance import build_replay_command

    model = _model_with_provenance(replay=False)
    check = cli_replay_check(model)
    assert check["available"] is True
    assert check["drifted"] is False


def test_cli_replay_check_flags_a_stale_snapshot():
    model = _model_with_provenance()
    model["provenance"]["replay"]["cli"]["command"] = "python main.py --model WRONG"
    check = cli_replay_check(model)
    assert check["drifted"] is True


def test_cli_replay_check_handles_legacy_model():
    check = cli_replay_check(_legacy_model())
    assert check["available"] is False
    assert check["drifted"] is False


# ── Registry integration ─────────────────────────────────────────────────────


@pytest.fixture
def registry(tmp_path):
    return RegistryManager(registry_base=tmp_path / "registry")


def test_registry_coverage_on_empty_registry(registry):
    audit = registry.provenance_coverage()
    assert audit["summary"]["total"] == 0
    assert audit["report"]["blocked"] == 0
    assert audit["models"] == []


def test_registry_coverage_counts_legacy_and_new_models(registry):
    """A legacy record on disk and a freshly saved (v13) record side by side."""
    models_dir = registry.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    legacy = _legacy_model("legacy-1")
    legacy["id"] = "legacy-1"
    (models_dir / "legacy-1.json").write_text(json.dumps(legacy, indent=2), encoding="utf-8")

    registry.save_model(
        model=None,
        model_type="SVM",
        hyperparameters={"C": 1.0},
        dataset_name="circles",
        n_samples=400,
        train_accuracy=0.8,
        test_accuracy=0.79,
    )

    audit = registry.provenance_coverage()
    assert audit["summary"]["total"] == 2
    assert audit["summary"]["with_provenance"] == 1
    assert audit["summary"]["with_replay"] == 1
    assert audit["summary"]["by_status"]["no_provenance"] == 1


def test_registry_coverage_does_not_rewrite_legacy_files(registry):
    legacy = _legacy_model("legacy-1")
    models_dir = registry.models_dir
    models_dir.mkdir(parents=True, exist_ok=True)
    path = models_dir / "legacy-1.json"
    original = json.dumps(legacy, indent=2)
    path.write_text(original, encoding="utf-8")

    registry.provenance_coverage()

    assert path.read_text(encoding="utf-8") == original


def test_registry_coverage_is_read_only_for_provenance_models(registry):
    registry.save_model(
        model=None,
        model_type="SVM",
        hyperparameters={"C": 1.0},
        dataset_name="circles",
        n_samples=500,
        train_accuracy=0.8,
        test_accuracy=0.79,
    )
    model_id = registry.list_models()[0]["id"]
    before = (registry.models_dir / f"{model_id}.json").read_text(encoding="utf-8")
    registry.provenance_coverage()
    after = (registry.models_dir / f"{model_id}.json").read_text(encoding="utf-8")
    assert before == after


# ── SDK integration ──────────────────────────────────────────────────────────


def test_sdk_coverage_returns_summary_report_and_models(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    audit = db.coverage()
    assert set(audit) == {"summary", "report", "models"}
    assert audit["summary"]["total"] == 0


def test_sdk_coverage_summary_helper(tmp_path):
    db = MLDB(registry_base=str(tmp_path / "registry"))
    summary = db.coverage_summary()
    assert summary["total"] == 0
    assert "by_status" in summary


# ── CLI surface ──────────────────────────────────────────────────────────────


def _run_cli(args, cwd=REPO_ROOT):
    env = dict(os.environ)
    env["PYTHONPATH"] = REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    return subprocess.run(
        [sys.executable, "main.py"] + args,
        cwd=cwd, env=env, capture_output=True, text=True, timeout=300,
    )


def test_cli_coverage_action_runs(tmp_path):
    env_dir = tmp_path / "registry"
    result = subprocess.run(
        [sys.executable, "main.py", "model", "coverage"],
        cwd=REPO_ROOT, env={**os.environ, "MLDB_REGISTRY_BASE": str(env_dir)},
        capture_output=True, text=True, timeout=300,
    )
    assert result.returncode == 0
    # An empty registry reports the empty-state message.
    assert "No models registered yet" in result.stdout


def test_cli_replay_run_flag_is_accepted():
    result = subprocess.run(
        [sys.executable, "main.py", "model", "replay", "--help"],
        cwd=REPO_ROOT, capture_output=True, text=True, timeout=120,
    )
    assert result.returncode == 0
    assert "--run" in result.stdout


# ── HTTP contract ────────────────────────────────────────────────────────────


def test_api_provenance_coverage_mode_via_flask_test_client(tmp_path):
    from web.server import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/api/provenance?coverage=1")
        assert response.status_code == 200
        payload = response.get_json()
        assert "summary" in payload
        assert "report" in payload
        assert "models" in payload
        assert payload["summary"]["total"] >= 0


def test_api_provenance_still_requires_id_without_coverage(tmp_path):
    from web.server import app

    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.get("/api/provenance")
        assert response.status_code == 400
        assert "id" in response.get_json()["error"]


def test_api_provenance_coverage_mode_via_serverless_handler(tmp_path, monkeypatch):
    import api.provenance as serverless

    class _Req:
        args = {"coverage": "1"}

    class _Res:
        status = 200
        payload = None

        def json(self, data):
            self.payload = data

    monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path / "registry"))
    res = _Res()
    serverless.handle(_Req(), res)
    assert res.status == 200
    assert "summary" in res.payload
