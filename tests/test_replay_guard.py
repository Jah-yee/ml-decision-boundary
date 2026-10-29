"""Tests for the replay integrity guard (v13 DoD #4).

The guard's whole job is to tell a *cosmetic* difference (the recipe is
spelled differently but reproduces the same run) apart from a *semantic* one
(the recipe would reproduce a different model).  The tests below pin both
halves: the semantic cases must be detected, and the cosmetic ones must not
raise false alarms.
"""
from __future__ import annotations

import copy

import pytest

from core.provenance import build_provenance, build_replay_command
from core.replay_guard import (
    DRIFT_LEVELS,
    classify_recipe_drift,
    integrity_report,
    verify_replay,
)


# ── Helpers ─────────────────────────────────────────────────────────────────

def _provenance(**overrides):
    """A provenance record with a frozen CLI replay recipe attached."""
    base = build_provenance(
        seed=42,
        dataset_name="circles",
        n_samples=500,
        noise=0.3,
        test_size=0.2,
        hyperparameters={"C": 1.0},
        model_type="SVM",
    )
    base["replay"] = {
        "sdk": "db = MLDB(seed=42)\nresult = db.train(...)",
        "cli": build_replay_command(base),
        "dependencies": {"requirements_lock_sha256": "abc123"},
        "expected": {"fingerprint": base.get("fingerprint")},
    }
    base.update(overrides)
    return base


def _model(model_id="2026-10-27_abc123", provenance=None, **overrides):
    model = {
        "id": model_id,
        "provenance": _provenance() if provenance is None else provenance,
    }
    model.update(overrides)
    return model


def _freeze(model_id, provenance, command):
    """Return a model whose stored recipe is exactly ``command``."""
    frozen = copy.deepcopy(provenance)
    frozen["replay"]["cli"] = dict(frozen["replay"]["cli"])
    frozen["replay"]["cli"]["command"] = command
    return _model(model_id=model_id, provenance=frozen)


# ── classify_recipe_drift: no drift ─────────────────────────────────────────

def test_identical_recipe_has_no_drift():
    provenance = _provenance()
    verdict = classify_recipe_drift(_model(provenance=provenance))
    assert verdict["drift"] == "none"
    assert verdict["changed_fields"] == []
    assert verdict["reproduces_same_model"] is True
    assert verdict["reason"] == ""


def test_model_without_provenance_is_not_drifted():
    verdict = classify_recipe_drift({"id": "legacy", "provenance": {}})
    assert verdict["drift"] == "none"
    assert verdict["reproduces_same_model"] is True
    assert "provenance" in verdict["reason"]


def test_model_without_frozen_recipe_is_not_drifted():
    provenance = _provenance()
    provenance["replay"] = {}
    verdict = classify_recipe_drift(_model(provenance=provenance))
    assert verdict["drift"] == "none"
    assert "no frozen" in verdict["reason"]


def test_drift_level_is_reported_in_changed_fields():
    provenance = _provenance()
    provenance["replay"]["cli"]["command"] = "python main.py --model SVM --dataset moons --seed 1"
    verdict = classify_recipe_drift(_model(provenance=provenance))
    assert verdict["drift"] == "semantic"
    assert "--dataset" in verdict["changed_fields"]


# ── classify_recipe_drift: cosmetic drift must NOT be semantic ──────────────

def test_tuple_vs_list_rendering_is_cosmetic():
    """`(50,)` and `[50]` denote the same hyperparameter.

    This is the real-world case: the recipe was frozen while the
    hyperparameter was still a Python tuple, and the record was later
    round-tripped through JSON, which turns the tuple into a list.  The
    stored command still says ``(50,)`` while today's code renders ``[50]``.
    """
    provenance = build_provenance(
        seed=42,
        dataset_name="circles",
        n_samples=500,
        noise=0.3,
        test_size=0.2,
        hyperparameters={"hidden_layer_sizes": (50,)},
        model_type="MLP",
    )
    provenance["replay"] = {
        "cli": {
            "command": "python main.py --model MLP --dataset circles --seed 42 --params 'hidden_layer_sizes=(50,)'",
            "exact": False,
            "warnings": [],
        }
    }
    # Simulate the JSON round-trip: the tuple became a list on disk.
    provenance["hyperparameters"] = {"hidden_layer_sizes": [50]}
    verdict = classify_recipe_drift(_model(provenance=provenance))
    assert verdict["drift"] == "cosmetic"
    assert verdict["reproduces_same_model"] is True


def test_visual_only_flag_difference_is_cosmetic():
    """`--n-samples` / `--noise` do not take part in the CLI training path."""
    provenance = _provenance()
    stored = (
        "python main.py --model SVM --dataset circles --n-samples 500 "
        "--noise 0.3 --seed 42 --params C=1.0"
    )
    model = _freeze("2026-10-26_1", provenance, stored)
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "cosmetic"
    assert verdict["reproduces_same_model"] is True


def test_numeric_equivalent_params_are_cosmetic():
    """`C=1` and `C=1.0` denote the same hyperparameter."""
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_2",
        provenance,
        "python main.py --model SVM --dataset circles --seed 42 --params C=1",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "cosmetic"
    assert verdict["reproduces_same_model"] is True


def test_reordered_params_are_cosmetic():
    """The order of the `--params` pairs does not change the run."""
    provenance = _provenance(
        hyperparameters={"C": 1.0, "kernel": "rbf"},
    )
    provenance["replay"]["cli"] = {
        "command": "python main.py --model SVM --dataset circles --seed 42 --params C=1.0 --params kernel=rbf",
        "exact": True,
        "warnings": [],
    }
    model = _freeze(
        "2026-10-26_3",
        provenance,
        "python main.py --model SVM --dataset circles --seed 42 --params kernel=rbf --params C=1.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "cosmetic"
    assert verdict["reproduces_same_model"] is True


# ── classify_recipe_drift: semantic drift MUST be detected ─────────────────

def test_changed_dataset_is_semantic():
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_4",
        provenance,
        "python main.py --model SVM --dataset moons --seed 42 --params C=1.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "--dataset" in verdict["changed_fields"]
    assert verdict["reproduces_same_model"] is False


def test_changed_seed_is_semantic():
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_5",
        provenance,
        "python main.py --model SVM --dataset circles --seed 7 --params C=1.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "--seed" in verdict["changed_fields"]


def test_changed_model_type_is_semantic():
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_6",
        provenance,
        "python main.py --model LR --dataset circles --seed 42 --params C=1.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "--model" in verdict["changed_fields"]


def test_changed_hyperparameter_value_is_semantic():
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_7",
        provenance,
        "python main.py --model SVM --dataset circles --seed 42 --params C=10.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "hyperparameters" in verdict["changed_fields"]
    assert verdict["reproduces_same_model"] is False


def test_added_hyperparameter_is_semantic():
    provenance = _provenance()
    model = _freeze(
        "2026-10-26_8",
        provenance,
        "python main.py --model SVM --dataset circles --seed 42 --params C=1.0 --params gamma=0.1",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "hyperparameters" in verdict["changed_fields"]


def test_removed_hyperparameter_is_semantic():
    provenance = _provenance(
        hyperparameters={"C": 1.0, "kernel": "rbf"},
    )
    provenance["replay"]["cli"] = {
        "command": "python main.py --model SVM --dataset circles --seed 42 --params C=1.0 --params kernel=rbf",
        "exact": True,
        "warnings": [],
    }
    model = _freeze(
        "2026-10-26_9",
        provenance,
        "python main.py --model SVM --dataset circles --seed 42 --params C=1.0",
    )
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] == "semantic"
    assert "hyperparameters" in verdict["changed_fields"]


def test_sequence_content_change_is_semantic():
    """`(50,)` → `(100,)` is a different model even though both are tuples."""
    provenance = build_provenance(
        seed=42,
        dataset_name="circles",
        n_samples=500,
        noise=0.3,
        test_size=0.2,
        hyperparameters={"hidden_layer_sizes": (50,)},
        model_type="MLP",
    )
    provenance["replay"] = {
        "cli": {
            "command": "python main.py --model MLP --dataset circles --seed 42 --params 'hidden_layer_sizes=(100,)'",
            "exact": False,
            "warnings": [],
        }
    }
    verdict = classify_recipe_drift(_model(provenance=provenance))
    assert verdict["drift"] == "semantic"
    assert "hyperparameters" in verdict["changed_fields"]


def test_malformed_command_does_not_crash():
    provenance = _provenance()
    model = _freeze("2026-10-26_10", provenance, "python main.py --model 'unclosed")
    verdict = classify_recipe_drift(model)
    assert verdict["drift"] in DRIFT_LEVELS


# ── integrity_report ────────────────────────────────────────────────────────

def test_integrity_report_counts_every_model():
    models = [
        _model("a"),
        _freeze("b", _provenance(), "python main.py --model SVM --dataset moons --seed 42 --params C=1.0"),
        _model("c", provenance={}),
    ]
    report = integrity_report(models)
    assert report["total"] == 3
    assert report["with_provenance"] == 2
    assert report["by_drift"]["semantic"] == 1
    assert report["broken"] == 1
    assert report["stale"] == 1
    assert [m["model_id"] for m in report["models"]] == ["b"]


def test_integrity_report_on_empty_registry():
    report = integrity_report([])
    assert report["total"] == 0
    assert report["broken"] == 0
    assert report["stale"] == 0
    assert report["by_drift"] == {level: 0 for level in DRIFT_LEVELS}


def test_integrity_report_separates_cosmetic_from_semantic():
    models = [
        _freeze("cosmetic", _provenance(), "python main.py --model SVM --dataset circles --seed 42 --params C=1"),
        _freeze("semantic", _provenance(), "python main.py --model SVM --dataset moons --seed 42 --params C=1.0"),
    ]
    report = integrity_report(models)
    assert report["by_drift"]["cosmetic"] == 1
    assert report["by_drift"]["semantic"] == 1
    assert report["stale"] == 2
    assert report["broken"] == 1


def test_integrity_report_does_not_mutate_the_models():
    models = [_model("a")]
    before = copy.deepcopy(models)
    integrity_report(models)
    assert models == before


# ── verify_replay ───────────────────────────────────────────────────────────

def test_verify_replay_reports_reproduced():
    provenance = _provenance()

    def trainer(_prov):
        return {"accuracy": 0.79, "reproduced": True}

    result = verify_replay("m1", provenance, expected_accuracy=0.79, trainer=trainer)
    assert result["verified"] is True
    assert result["status"] == "reproduced"
    assert result["accuracy_delta"] == 0.0


def test_verify_replay_reports_drifted():
    provenance = _provenance()

    def trainer(_prov):
        return {"accuracy": 0.71, "reproduced": False}

    result = verify_replay("m1", provenance, expected_accuracy=0.79, trainer=trainer)
    assert result["status"] == "drifted"
    assert result["reproduced"] is False
    assert result["accuracy_delta"] == pytest.approx(-0.08)


def test_verify_replay_infers_reproduction_from_the_accuracy_delta():
    provenance = _provenance()

    def trainer(_prov):
        return {"accuracy": 0.79}

    result = verify_replay("m1", provenance, expected_accuracy=0.79, trainer=trainer)
    assert result["status"] == "reproduced"
    assert result["reproduced"] is True


def test_verify_replay_without_provenance():
    result = verify_replay("m1", {}, expected_accuracy=0.79)
    assert result["verified"] is False
    assert result["status"] == "no_provenance"


def test_verify_replay_without_a_trainer_does_not_execute():
    provenance = _provenance()
    result = verify_replay("m1", provenance, expected_accuracy=0.79)
    assert result["verified"] is False
    assert result["status"] == "not_verified"
    assert "not executed" in result["reason"]


def test_verify_replay_surfaces_a_raising_trainer():
    provenance = _provenance()

    def trainer(_prov):
        raise RuntimeError("boom")

    result = verify_replay("m1", provenance, expected_accuracy=0.79, trainer=trainer)
    assert result["status"] == "error"
    assert result["verified"] is False
    assert "boom" in result["reason"]


def test_verify_replay_carries_the_drift_verdict():
    provenance = _provenance()
    model = _freeze(
        "m2",
        provenance,
        "python main.py --model SVM --dataset moons --seed 42 --params C=1.0",
    )

    def trainer(_prov):
        return {"accuracy": 0.79, "reproduced": True}

    result = verify_replay(
        "m2",
        model["provenance"],
        expected_accuracy=0.79,
        trainer=trainer,
    )
    assert result["drift"]["drift"] == "semantic"
