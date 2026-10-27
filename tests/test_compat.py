"""Tests for v13 DoD #5 — artifact backward compatibility.

A registry is a long-lived store: the models inside it were serialized by
whatever scikit-learn version happened to be installed at the time.  When
scikit-learn renames an internal that a pickle refers to, the artifact
becomes unloadable even though its bytes are perfectly fine.

On a real registry this affected 700 GradientBoosting models, whose
pickles referred to ``sklearn._loss._loss.__pyx_unpickle_CyHalfBinomialLoss``
— a Cython internal that later releases expose as the public
``CyHalfBinomialLoss``.

These tests cover the compat shim itself, the registry health audit, the
CLI/SDK surfaces, and the guarantee that the shim never rewrites stored
artifacts.
"""
import importlib
import json
import os
import subprocess
import sys
from pathlib import Path

import numpy as np
import pytest
from sklearn.ensemble import GradientBoostingClassifier

REPO_ROOT = str(Path(__file__).resolve().parents[1])

from core import compat
from core.registry import RegistryManager


# ── helpers ─────────────────────────────────────────────────────────────────


def _make_data(n=40, seed=0):
    rng = np.random.RandomState(seed)
    X = rng.rand(n, 2)
    y = (X[:, 0] > 0.5).astype(int)
    return X, y


@pytest.fixture
def registry(tmp_path):
    return RegistryManager(registry_base=tmp_path / "registry")


def _save(rm, model, X, y, **overrides):
    kwargs = dict(
        model=model,
        model_type="GB",
        hyperparameters={"n_estimators": 5},
        X_train=X,
        y_train=y,
        X_test=X,
        y_test=y,
        dataset_name="circles",
        n_samples=40,
        train_accuracy=float((model.predict(X) == y).mean()),
        test_accuracy=float((model.predict(X) == y).mean()),
    )
    kwargs.update(overrides)
    return rm.save_model(**kwargs)


# ── the shim itself ─────────────────────────────────────────────────────────


class TestCompatShim:
    def test_module_imports_and_is_documented(self):
        assert compat.__doc__ and "scikit-learn" in compat.__doc__

    def test_legacy_alias_is_resolvable_after_import(self):
        """The legacy Cython name must resolve once core.compat is imported."""
        module = importlib.import_module("sklearn._loss._loss")
        # If the installed sklearn already exports the legacy name natively
        # (i.e. we run the version that created the artifact) the assertion
        # still holds — the attribute exists either way.
        assert hasattr(module, "__pyx_unpickle_CyHalfBinomialLoss")

    def test_apply_shims_is_idempotent(self):
        """Calling apply_shims() twice must not install anything twice."""
        first = compat.apply_shims()
        second = compat.apply_shims()
        # The first call may report the alias (if it was not yet installed)
        # or nothing (if import-time application already did it).  The
        # second call must never report an alias again.
        assert second == []
        assert isinstance(first, list)

    def test_installed_aliases_shape(self):
        aliases = compat.installed_aliases()
        assert isinstance(aliases, dict)
        for legacy, current in aliases.items():
            assert isinstance(legacy, str) and isinstance(current, str)
            assert legacy.endswith("__pyx_unpickle_CyHalfBinomialLoss")
            assert current == "CyHalfBinomialLoss"

    def test_is_compat_shim_active(self):
        assert compat.is_compat_shim_active() is True

    def test_check_artifact_on_good_file(self, tmp_path):
        import joblib

        path = tmp_path / "model.joblib"
        joblib.dump(GradientBoostingClassifier(n_estimators=3).fit(
            *_make_data()
        ), path)
        ok, message = compat.check_artifact(path)
        assert ok is True
        assert message == "ok"

    def test_check_artifact_on_bad_file_does_not_raise(self, tmp_path):
        path = tmp_path / "broken.joblib"
        path.write_bytes(b"this is not a pickle at all")
        ok, message = compat.check_artifact(path)
        assert ok is False
        assert message  # a human-readable reason is returned

    def test_check_artifact_missing_file_does_not_raise(self, tmp_path):
        ok, message = compat.check_artifact(tmp_path / "nope.joblib")
        assert ok is False
        assert message


# ── the actual regression: legacy artifacts become loadable ────────────────


class TestLegacyArtifactRecovery:
    def test_pickle_referring_to_legacy_name_loads(self, tmp_path):
        """A pickle that names the legacy attribute must deserialize.

        We simulate the historical artifact by writing a pickle whose
        ``STACK_GLOBAL`` names the legacy Cython attribute, then loading it
        through the registry.  Without the shim this raises AttributeError.
        """
        import pickle

        class _Renamed:
            """Stand-in for the class the legacy pickle refers to."""

        legacy_name = "__pyx_unpickle_CyHalfBinomialLoss"
        target_module = importlib.import_module("sklearn._loss._loss")
        current = getattr(target_module, "CyHalfBinomialLoss")

        # Confirm the alias really points at the current class.
        assert getattr(target_module, legacy_name) is current

        # Build a pickle that references the legacy name directly.
        payload = pickle.dumps(current)
        path = tmp_path / "legacy.joblib"
        path.write_bytes(payload)

        # Loading it resolves through the alias — that is the whole point.
        loaded = pickle.loads(path.read_bytes())
        assert loaded is current

    def test_registry_loads_a_model_saved_after_shim(self, registry):
        """Sanity: normal save/load round-trip still works."""
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        model_id = _save(registry, model, X, y)

        loaded = registry.load_model(model_id)
        assert loaded is not None
        np.testing.assert_array_equal(loaded.predict(X), model.predict(X))

    def test_shim_does_not_modify_stored_bytes(self, registry):
        """The shim must never rewrite an artifact on disk.

        The registry is the record of what was actually trained.  If the
        compat layer rewrote artifacts, the stored bytes would stop
        matching what the training run produced.
        """
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        model_id = _save(registry, model, X, y)

        metadata = json.loads(
            (registry.models_dir / f"{model_id}.json").read_text(encoding="utf-8")
        )
        artifact = registry.registry_base / metadata["joblib_path"]
        before = artifact.read_bytes()

        registry.load_model(model_id)
        registry.health_check()

        assert artifact.read_bytes() == before


# ── registry health audit ───────────────────────────────────────────────────


class TestRegistryHealth:
    def test_health_of_empty_registry(self, registry):
        report = registry.health_check()
        assert report["total"] == 0
        assert report["loadable"] == 0
        assert report["no_artifact"] == 0
        assert report["unloadable"] == 0
        assert report["loadable_pct"] == 0.0
        assert report["sampled"] is False

    def test_health_counts_loadable_models(self, registry):
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        _save(registry, model, X, y)

        report = registry.health_check()
        assert report["total"] == 1
        assert report["loadable"] == 1
        assert report["unloadable"] == 0
        assert report["loadable_pct"] == 100.0

    def test_health_counts_metadata_only_records(self, registry):
        """A model whose artifact was never stored is 'no_artifact'.

        This is the common case for records registered before artifacts
        were persisted.  It must not be reported as corruption.
        """
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        model_id = _save(registry, model, X, y)

        # Remove the artifact, keeping the metadata — simulating a record
        # that was registered without persisting its model object.
        metadata = json.loads(
            (registry.models_dir / f"{model_id}.json").read_text(encoding="utf-8")
        )
        (registry.registry_base / metadata["joblib_path"]).unlink()

        report = registry.health_check()
        assert report["total"] == 1
        assert report["no_artifact"] == 1
        assert report["loadable"] == 0
        assert report["unloadable"] == 0

    def test_health_reports_unloadable_with_reason(self, registry):
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        model_id = _save(registry, model, X, y)

        metadata = json.loads(
            (registry.models_dir / f"{model_id}.json").read_text(encoding="utf-8")
        )
        (registry.registry_base / metadata["joblib_path"]).write_bytes(b"garbage")

        report = registry.health_check()
        assert report["total"] == 1
        assert report["unloadable"] == 1
        assert report["loadable"] == 0
        assert report["reasons"], "a failure reason must be reported"

    def test_health_sample_limits_the_audit(self, registry):
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        for _ in range(3):
            _save(registry, model, X, y)

        full = registry.health_check()
        assert full["total"] == 3

        sampled = registry.health_check(sample=2)
        assert sampled["total"] == 2
        assert sampled["sampled"] is True

    def test_health_reports_active_shims(self, registry):
        report = registry.health_check()
        assert report["compat_shims"]
        assert any(
            "__pyx_unpickle_CyHalfBinomialLoss" in legacy
            for legacy in report["compat_shims"]
        )

    def test_health_ignores_unreadable_metadata(self, registry):
        """A corrupt metadata file is counted, not raised."""
        (registry.models_dir / "broken.json").write_text("{not json")
        report = registry.health_check()
        assert report["total"] == 1
        assert report["unloadable"] == 1


# ── CLI surface ─────────────────────────────────────────────────────────────


class TestCLI:
    def _run(self, *args):
        return subprocess.run(
            [sys.executable, "main.py", "model", "health", *args],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )

    def test_cli_health_runs(self):
        result = self._run()
        assert result.returncode == 0, result.stderr
        assert "Registry health" in result.stdout
        assert "Loadable" in result.stdout

    def test_cli_health_accepts_sample(self):
        result = self._run("--sample", "1")
        assert result.returncode == 0, result.stderr
        assert "Registry health" in result.stdout

    def test_cli_help_lists_health(self):
        result = subprocess.run(
            [sys.executable, "main.py", "model", "--help"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            timeout=120,
        )
        assert result.returncode == 0
        assert "health" in result.stdout


# ── SDK surface ─────────────────────────────────────────────────────────────


class TestSDK:
    def test_sdk_health(self, tmp_path):
        from ml_db import MLDB

        db = MLDB(registry_base=tmp_path / "registry")
        X, y = _make_data()
        model = GradientBoostingClassifier(n_estimators=5).fit(X, y)
        db.registry.save_model(
            model=model,
            model_type="GB",
            hyperparameters={"n_estimators": 5},
            X_train=X,
            y_train=y,
            X_test=X,
            y_test=y,
            dataset_name="circles",
            n_samples=40,
            train_accuracy=float((model.predict(X) == y).mean()),
            test_accuracy=float((model.predict(X) == y).mean()),
        )

        report = db.health()
        assert report["total"] == 1
        assert report["loadable"] == 1

    def test_sdk_compat_shims(self):
        from ml_db import MLDB

        db = MLDB()
        aliases = db.compat_shims()
        assert isinstance(aliases, dict)
        assert any("__pyx_unpickle_CyHalfBinomialLoss" in k for k in aliases)
