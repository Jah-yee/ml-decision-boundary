"""
tests/test_registry_versioning.py — v12 DoD #3: Registry improvements

Covers:
- Model versioning (v1/v2/v3) within a family (type + dataset + params)
- Family key determinism and grouping
- Legacy (pre-v12) metadata normalization — backward compatibility
- Batch tag query (`list_models_by_tags`) with `any` / `all` modes
- `tag_index()` ordering
- SDK passthrough (ml_db.MLDB)
- HTTP API contract (/api/registry)
"""

import json

import pytest
from sklearn.svm import SVC
from sklearn.datasets import make_circles

from core.registry import RegistryManager
from ml_db.client import MLDB


@pytest.fixture
def temp_registry(tmp_path):
    """Temporary registry root for isolated testing."""
    rm = RegistryManager(registry_base=tmp_path)
    rm._ensure_dirs()
    return rm


@pytest.fixture
def trained_svm():
    """Pre-trained SVM on synthetic data."""
    X, y = make_circles(n_samples=100, noise=0.2, random_state=42)
    model = SVC(kernel="rbf", C=1.0, gamma="scale")
    model.fit(X, y)
    return model, X, y


def _save(rm, model, X, y, model_type="SVM", dataset="circles", params=None, acc=0.9):
    """Helper: register a model with the given identity."""
    return rm.save_model(
        model,
        model_type=model_type,
        hyperparameters=params if params is not None else {"C": 1.0, "gamma": "scale"},
        X_train=X,
        y_train=y,
        dataset_name=dataset,
        n_samples=len(X),
        train_accuracy=acc,
        test_accuracy=acc,
    )


# ── Family key ────────────────────────────────────────────────────────────────


class TestFamilyKey:
    def test_family_key_is_deterministic(self):
        a = RegistryManager.family_key("SVM", "circles", {"C": 1.0, "gamma": "scale"})
        b = RegistryManager.family_key("SVM", "circles", {"C": 1.0, "gamma": "scale"})
        assert a == b

    def test_family_key_is_param_order_independent(self):
        a = RegistryManager.family_key("SVM", "circles", {"C": 1.0, "gamma": "scale"})
        b = RegistryManager.family_key("SVM", "circles", {"gamma": "scale", "C": 1.0})
        assert a == b

    def test_family_key_differs_by_model_type(self):
        a = RegistryManager.family_key("SVM", "circles", {"C": 1.0})
        b = RegistryManager.family_key("RF", "circles", {"C": 1.0})
        assert a != b

    def test_family_key_differs_by_dataset(self):
        a = RegistryManager.family_key("SVM", "circles", {"C": 1.0})
        b = RegistryManager.family_key("SVM", "moons", {"C": 1.0})
        assert a != b

    def test_family_key_differs_by_params(self):
        a = RegistryManager.family_key("SVM", "circles", {"C": 1.0})
        b = RegistryManager.family_key("SVM", "circles", {"C": 10.0})
        assert a != b

    def test_family_key_handles_empty_inputs(self):
        key = RegistryManager.family_key("", "", {})
        assert key == "unknown|unknown"


# ── Versioning ────────────────────────────────────────────────────────────────


class TestModelVersioning:
    def test_first_model_is_v1(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        mid = _save(temp_registry, model, X, y)
        meta = temp_registry.get_metadata(mid)
        assert meta["version"] == 1
        assert meta["family"]

    def test_second_identical_model_is_v2(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        first = _save(temp_registry, model, X, y)
        second = _save(temp_registry, model, X, y)
        assert temp_registry.get_metadata(first)["version"] == 1
        assert temp_registry.get_metadata(second)["version"] == 2

    def test_third_identical_model_is_v3(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        for _ in range(3):
            _save(temp_registry, model, X, y)
        versions = sorted(m["version"] for m in temp_registry.list_models())
        assert versions == [1, 2, 3]

    def test_different_params_start_at_v1(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a = _save(temp_registry, model, X, y, params={"C": 1.0})
        b = _save(temp_registry, model, X, y, params={"C": 99.0})
        assert temp_registry.get_metadata(a)["version"] == 1
        assert temp_registry.get_metadata(b)["version"] == 1

    def test_different_model_type_starts_at_v1(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a = _save(temp_registry, model, X, y, model_type="SVM")
        b = _save(temp_registry, model, X, y, model_type="RF")
        assert temp_registry.get_metadata(b)["version"] == 1
        assert (
            temp_registry.get_metadata(a)["family"]
            != temp_registry.get_metadata(b)["family"]
        )

    def test_different_dataset_starts_at_v1(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a = _save(temp_registry, model, X, y, dataset="circles")
        b = _save(temp_registry, model, X, y, dataset="moons")
        assert temp_registry.get_metadata(b)["version"] == 1

    def test_version_is_persisted_to_json(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        mid = _save(temp_registry, model, X, y)
        raw = json.loads((temp_registry.models_dir / f"{mid}.json").read_text())
        assert raw["version"] == 1
        assert "family" in raw

    def test_get_model_versions_returns_all(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        first = _save(temp_registry, model, X, y)
        second = _save(temp_registry, model, X, y)
        versions = temp_registry.get_model_versions(first)
        assert len(versions) == 2
        assert [v["version"] for v in versions] == [1, 2]
        assert {v["id"] for v in versions} == {first, second}

    def test_get_model_versions_for_new_family(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        mid = _save(temp_registry, model, X, y)
        versions = temp_registry.get_model_versions(mid)
        assert len(versions) == 1
        assert versions[0]["id"] == mid

    def test_get_model_versions_unknown_raises(self, temp_registry):
        with pytest.raises(FileNotFoundError):
            temp_registry.get_model_versions("nope")

    def test_get_latest_version(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        first = _save(temp_registry, model, X, y)
        second = _save(temp_registry, model, X, y)
        assert temp_registry.get_latest_version(first)["id"] == second
        assert temp_registry.get_latest_version(first)["version"] == 2

    def test_get_latest_version_unknown_raises(self, temp_registry):
        with pytest.raises(FileNotFoundError):
            temp_registry.get_latest_version("nope")

    def test_list_model_families_groups_versions(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        _save(temp_registry, model, X, y)
        _save(temp_registry, model, X, y)
        _save(temp_registry, model, X, y, model_type="RF")
        families = temp_registry.list_model_families()
        assert len(families) == 2
        counts = sorted(len(v) for v in families.values())
        assert counts == [1, 2]

    def test_list_model_families_orders_versions_ascending(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        _save(temp_registry, model, X, y)
        _save(temp_registry, model, X, y)
        families = temp_registry.list_model_families()
        members = next(iter(families.values()))
        assert [m["version"] for m in members] == [1, 2]


# ── Legacy backward compatibility ─────────────────────────────────────────────


class TestLegacyCompatibility:
    def _write_legacy(self, rm, model_id, **overrides):
        """Write a metadata file the way pre-v12 code did (no version/family)."""
        payload = {
            "id": model_id,
            "model_type": "SVM",
            "hyperparameters": {"C": 1.0, "gamma": "scale"},
            "dataset": {"name": "circles", "n_samples": 100, "hash": "unknown"},
            "metrics": {"train_accuracy": 0.9, "test_accuracy": 0.88},
            "created_at": "2026-01-01T00:00:00+00:00",
            "plugin_origin": False,
            "joblib_path": f"models/{model_id}.joblib",
            "accuracy": 0.88,
        }
        payload.update(overrides)
        (rm.models_dir / f"{model_id}.json").write_text(json.dumps(payload))

    def test_legacy_metadata_defaults_to_version_1(self, temp_registry):
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        meta = temp_registry.get_metadata("2026-01-01_legacy01")
        assert meta["version"] == 1
        assert meta["family"]

    def test_legacy_family_is_derived(self, temp_registry):
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        meta = temp_registry.get_metadata("2026-01-01_legacy01")
        expected = RegistryManager.family_key(
            "SVM", "circles", {"C": 1.0, "gamma": "scale"}
        )
        assert meta["family"] == expected

    def test_legacy_model_lists_normally(self, temp_registry):
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        models = temp_registry.list_models()
        assert len(models) == 1
        assert models[0]["version"] == 1

    def test_new_model_after_legacy_becomes_v2(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        mid = _save(temp_registry, model, X, y)
        assert temp_registry.get_metadata(mid)["version"] == 2

    def test_legacy_models_group_into_family(self, temp_registry):
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        self._write_legacy(temp_registry, "2026-01-02_legacy02")
        families = temp_registry.list_model_families()
        assert len(families) == 1
        assert len(next(iter(families.values()))) == 2

    def test_reading_legacy_file_does_not_rewrite_it(self, temp_registry):
        """Reading must not touch the file — no silent migration.  v12 DoD #3."""
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        path = temp_registry.models_dir / "2026-01-01_legacy01.json"
        before = path.read_text()

        temp_registry.get_metadata("2026-01-01_legacy01")
        temp_registry.list_models()
        temp_registry.list_model_families()
        temp_registry.get_model_versions("2026-01-01_legacy01")

        assert path.read_text() == before
        assert "version" not in json.loads(before)
        assert "family" not in json.loads(before)

    def test_tagging_legacy_model_does_not_add_version_or_family(self, temp_registry):
        """Tagging writes only the tags field — legacy file keeps its shape."""
        self._write_legacy(temp_registry, "2026-01-01_legacy01")
        path = temp_registry.models_dir / "2026-01-01_legacy01.json"

        temp_registry.tag_model("2026-01-01_legacy01", "prod")

        stored = json.loads(path.read_text())
        assert stored["tags"] == ["prod"]
        assert "version" not in stored
        assert "family" not in stored
        # ...but the derived values are still visible through the read path
        meta = temp_registry.get_metadata("2026-01-01_legacy01")
        assert meta["version"] == 1
        assert meta["family"]

    def test_untagging_legacy_model_does_not_add_version_or_family(self, temp_registry):
        self._write_legacy(temp_registry, "2026-01-01_legacy01", tags=["prod"])
        path = temp_registry.models_dir / "2026-01-01_legacy01.json"

        temp_registry.untag_model("2026-01-01_legacy01", "prod")

        stored = json.loads(path.read_text())
        assert stored["tags"] == []
        assert "version" not in stored
        assert "family" not in stored


# ── Batch tag query ───────────────────────────────────────────────────────────


class TestBatchTagQuery:
    def _setup(self, rm, model, X, y):
        a = _save(rm, model, X, y)
        b = _save(rm, model, X, y)
        c = _save(rm, model, X, y)
        rm.tag_model(a, "prod")
        rm.tag_model(a, "best")
        rm.tag_model(b, "prod")
        rm.tag_model(c, "experimental")
        return a, b, c

    def test_single_tag_works_like_list_models_by_tag(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        result = temp_registry.list_models_by_tags(["prod"])
        assert {m["id"] for m in result} == {a, b}

    def test_any_mode_is_union(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        result = temp_registry.list_models_by_tags(["prod", "experimental"], mode="any")
        assert {m["id"] for m in result} == {a, b, c}

    def test_all_mode_is_intersection(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        result = temp_registry.list_models_by_tags(["prod", "best"], mode="all")
        assert {m["id"] for m in result} == {a}

    def test_all_mode_excludes_partial_matches(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        result = temp_registry.list_models_by_tags(["prod", "experimental"], mode="all")
        assert result == []

    def test_unknown_tag_returns_empty(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        self._setup(temp_registry, model, X, y)
        assert temp_registry.list_models_by_tags(["nope"]) == []

    def test_empty_tag_list_raises(self, temp_registry):
        with pytest.raises(ValueError):
            temp_registry.list_models_by_tags([])

    def test_blank_tag_list_raises(self, temp_registry):
        with pytest.raises(ValueError):
            temp_registry.list_models_by_tags(["", "  "])

    def test_invalid_mode_raises(self, temp_registry):
        with pytest.raises(ValueError):
            temp_registry.list_models_by_tags(["prod"], mode="xor")

    def test_results_are_newest_first(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        self._setup(temp_registry, model, X, y)
        result = temp_registry.list_models_by_tags(["prod", "experimental"], mode="any")
        created = [m["created_at"] for m in result]
        assert created == sorted(created, reverse=True)

    def test_tag_index_lists_ids(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        index = temp_registry.tag_index()
        assert set(index["prod"]) == {a, b}
        assert set(index["best"]) == {a}
        assert set(index["experimental"]) == {c}

    def test_tag_index_preserves_newest_first_order(self, temp_registry, trained_svm):
        model, X, y = trained_svm
        a, b, c = self._setup(temp_registry, model, X, y)
        index = temp_registry.tag_index()
        assert index["prod"] == [b, a]

    def test_list_tags_matches_tag_index(self, temp_registry, trained_svm):
        """v9 list_tags() stays compatible with the v12 tag_index()."""
        model, X, y = trained_svm
        self._setup(temp_registry, model, X, y)
        assert temp_registry.list_tags() == temp_registry.tag_index()


# ── SDK passthrough ───────────────────────────────────────────────────────────


class TestSDKPassthrough:
    def _register(self, db):
        X, y = make_circles(n_samples=100, noise=0.2, random_state=42)
        model = SVC(kernel="rbf", C=1.0, gamma="scale")
        model.fit(X, y)
        return db.registry.save_model(
            model,
            model_type="SVM",
            hyperparameters={"C": 1.0, "gamma": "scale"},
            X_train=X,
            y_train=y,
            dataset_name="circles",
            n_samples=len(X),
            train_accuracy=0.9,
            test_accuracy=0.88,
        )

    def test_sdk_exposes_versioning(self, tmp_path):
        db = MLDB(registry_base=tmp_path)
        mid = self._register(db)
        meta = db.get_model(mid)
        assert meta["version"] == 1
        assert len(db.get_model_versions(mid)) == 1
        assert db.get_latest_version(mid)["id"] == mid
        assert len(db.list_model_families()) == 1

    def test_sdk_exposes_batch_tag_query(self, tmp_path):
        db = MLDB(registry_base=tmp_path)
        mid = self._register(db)
        db.tag(mid, "prod")
        db.tag(mid, "best")
        assert len(db.list_models_by_tags(["prod", "best"], mode="all")) == 1
        assert len(db.list_models_by_tags(["prod", "nope"], mode="all")) == 0
        assert set(db.tag_index()["prod"]) == {mid}


# ── HTTP API contract ─────────────────────────────────────────────────────────


class _FakeRes:
    """Minimal Vercel-style response double."""

    def __init__(self):
        self.status = 200
        self.payload = None

    def json(self, data):
        self.payload = data


class _FakeReq:
    """Minimal Vercel-style request double."""

    def __init__(self, args=None):
        self.args = args or {}


class TestRegistryAPI:
    def _make_models(self, tmp_path):
        X, y = make_circles(n_samples=100, noise=0.2, random_state=42)
        model = SVC(kernel="rbf", C=1.0, gamma="scale")
        model.fit(X, y)
        db = MLDB(registry_base=tmp_path)
        ids = []
        for _ in range(2):
            ids.append(
                db.registry.save_model(
                    model,
                    model_type="SVM",
                    hyperparameters={"C": 1.0, "gamma": "scale"},
                    X_train=X,
                    y_train=y,
                    dataset_name="circles",
                    n_samples=len(X),
                    train_accuracy=0.9,
                    test_accuracy=0.88,
                )
            )
        db.tag(ids[0], "prod")
        db.tag(ids[0], "best")
        db.tag(ids[1], "prod")
        return db, ids

    @pytest.fixture(autouse=True)
    def _patch_db(self, tmp_path, monkeypatch):
        from api import registry as api_registry

        self.db, self.ids = self._make_models(tmp_path)
        monkeypatch.setattr(
            api_registry, "MLDB", lambda *a, **k: MLDB(registry_base=tmp_path)
        )

    def test_list_endpoint(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq(), res)
        assert res.status == 200
        assert res.payload["count"] == 2
        assert len(res.payload["models"]) == 2

    def test_batch_tag_endpoint(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"tags": "prod,best", "match": "all"}), res)
        assert res.status == 200
        assert res.payload["count"] == 1
        assert res.payload["match"] == "all"

    def test_batch_tag_endpoint_invalid_match(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"tags": "prod", "match": "bogus"}), res)
        assert res.status == 400
        assert "error" in res.payload

    def test_versions_endpoint(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"id": self.ids[0], "versions": "1"}), res)
        assert res.status == 200
        assert res.payload["count"] == 2
        assert [v["version"] for v in res.payload["versions"]] == [1, 2]

    def test_families_endpoint(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"families": "1"}), res)
        assert res.status == 200
        assert res.payload["count"] == 1
        assert res.payload["version_total"] == 2

    def test_unknown_model_returns_404(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"id": "nope"}), res)
        assert res.status == 404

    def test_empty_tags_returns_400(self, tmp_path):
        """An explicit but empty `tags` filter is a client error."""
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"tags": ""}), res)
        assert res.status == 400
        assert "error" in res.payload

    def test_blank_only_tags_returns_400(self, tmp_path):
        from api import registry as api_registry

        res = _FakeRes()
        api_registry.handle(_FakeReq({"tags": " , , "}), res)
        assert res.status == 400
        assert "error" in res.payload


class TestRegistryAPIContractParity:
    """The Vercel serverless handler and the local Flask route must agree.

    `api/registry.py` (production) and `web/server.py` (local dev) expose the
    same URL, so a response must not differ between the two deployments.
    """

    def _serverless(self, tmp_path, monkeypatch, **args):
        from api import registry as api_registry

        monkeypatch.setattr(
            api_registry, "MLDB", lambda *a, **k: MLDB(registry_base=tmp_path)
        )
        res = _FakeRes()
        api_registry.handle(_FakeReq(args), res)
        return res.status, res.payload

    def _flask(self, tmp_path, monkeypatch, query=""):
        from web.server import app

        monkeypatch.setenv("MLDB_REGISTRY_BASE", str(tmp_path))
        client = app.test_client()
        resp = client.get("/api/registry" + query)
        return resp.status_code, resp.get_json()

    @pytest.fixture
    def _registry(self, tmp_path, monkeypatch):
        X, y = make_circles(n_samples=100, noise=0.2, random_state=42)
        model = SVC(kernel="rbf", C=1.0, gamma="scale")
        model.fit(X, y)
        db = MLDB(registry_base=tmp_path)
        ids = [
            db.registry.save_model(
                model,
                model_type="SVM",
                hyperparameters={"C": 1.0, "gamma": "scale"},
                X_train=X,
                y_train=y,
                dataset_name="circles",
                n_samples=len(X),
                train_accuracy=0.9,
                test_accuracy=0.88,
            )
            for _ in range(2)
        ]
        db.tag(ids[0], "prod")
        db.tag(ids[0], "best")
        db.tag(ids[1], "prod")
        return ids

    @pytest.mark.parametrize(
        "query,kwargs",
        [
            ("", {}),
            ("?families=1", {"families": "1"}),
            ("?tags=prod", {"tags": "prod"}),
            ("?tags=prod,best&match=all", {"tags": "prod,best", "match": "all"}),
            ("?tags=prod&match=bogus", {"tags": "prod", "match": "bogus"}),
            ("?tags=", {"tags": ""}),
            ("?id=nope", {"id": "nope"}),
        ],
    )
    def test_status_codes_match(
        self, tmp_path, monkeypatch, _registry, query, kwargs
    ):
        sl_status, sl_body = self._serverless(tmp_path, monkeypatch, **kwargs)
        fl_status, fl_body = self._flask(tmp_path, monkeypatch, query)

        assert sl_status == fl_status, f"status mismatch for {query or '(no query)'}"
        assert sorted(sl_body.keys()) == sorted(fl_body.keys())

    def test_success_bodies_match(self, tmp_path, monkeypatch, _registry):
        sl_status, sl_body = self._serverless(tmp_path, monkeypatch, tags="prod")
        fl_status, fl_body = self._flask(tmp_path, monkeypatch, "?tags=prod")

        assert sl_status == fl_status == 200
        assert sl_body["count"] == fl_body["count"]
        assert sl_body["tags"] == fl_body["tags"]
        assert sl_body["match"] == fl_body["match"]
        assert [m["id"] for m in sl_body["models"]] == [
            m["id"] for m in fl_body["models"]
        ]
