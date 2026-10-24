"""
tests/test_api_models_datasets.py — v10 API endpoints: /api/models/<name> and /api/datasets

Tests the Vercel serverless entrypoints in api/models.py and api/datasets.py
and the Flask routes in web/server.py.

v10 DoD:
- DoD #1: GET /api/models/<name> returns model metadata
- DoD #2: GET /api/datasets returns dataset catalogue
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# Fake Vercel objects
# ─────────────────────────────────────────────────────────────────────────────

class FakeReq:
    def __init__(self, url, body=None):
        self.url = url
        self._body = body or {}

    def get_json(self):
        return self._body


class FakeRes:
    def __init__(self):
        self.status = None
        self.data = None

    def json(self, d):
        self.data = d


# ─────────────────────────────────────────────────────────────────────────────
# /api/datasets — Contract Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIDatasets:
    """Test /api/datasets serverless function."""

    def test_datasets_returns_list(self):
        from api.datasets import handle

        fr = FakeRes()
        handle(FakeReq('/api/datasets'), fr)
        assert fr.status is None, \
            f"Expected success, got status={fr.status}"
        assert 'datasets' in fr.data, \
            "Response must have 'datasets' key"
        assert 'count' in fr.data, \
            "Response must have 'count' key"
        assert isinstance(fr.data['datasets'], list), \
            "'datasets' must be a list"
        assert fr.data['count'] == len(fr.data['datasets']), \
            "count must match len(datasets)"

    def test_datasets_all_eight_present(self):
        from api.datasets import handle

        fr = FakeRes()
        handle(FakeReq('/api/datasets'), fr)
        names = {d['name'] for d in fr.data['datasets']}
        expected = {
            'circles', 'moons', 'blobs', 'xor', 's_curve',
            'swiss_roll', 'classification_2blobs', 'classification_concentric',
        }
        assert names == expected, \
            f"Expected datasets {expected}, got {names}"

    def test_datasets_have_required_fields(self):
        from api.datasets import handle

        fr = FakeRes()
        handle(FakeReq('/api/datasets'), fr)
        required = {'name', 'full_name', 'description', 'complexity',
                    'n_features', 'n_classes', 'recommended_for',
                    'parameters', 'defaults'}
        for ds in fr.data['datasets']:
            missing = required - set(ds.keys())
            assert not missing, \
                f"Dataset '{ds.get('name', '?')}' missing fields: {missing}"

    def test_datasets_parameters_have_type_and_range(self):
        from api.datasets import handle

        fr = FakeRes()
        handle(FakeReq('/api/datasets'), fr)
        for ds in fr.data['datasets']:
            for pname, pinfo in ds.get('parameters', {}).items():
                assert 'type' in pinfo, \
                    f"{ds['name']}/{pname}: 'type' field required"
                assert 'range' in pinfo or 'options' in pinfo, \
                    f"{ds['name']}/{pname}: 'range' or 'options' field required"

    def test_datasets_complexity_labels_valid(self):
        from api.datasets import handle

        fr = FakeRes()
        handle(FakeReq('/api/datasets'), fr)
        valid = {'low', 'medium', 'high'}
        for ds in fr.data['datasets']:
            assert ds['complexity'] in valid, \
                f"Dataset '{ds['name']}' complexity must be one of {valid}"


# ─────────────────────────────────────────────────────────────────────────────
# /api/models/<name> — Contract Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIModels:
    """Test /api/models/<name> serverless function."""

    def test_models_root_returns_list(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models'), fr)
        assert fr.status is None, \
            f"Expected success, got status={fr.status}"
        assert 'models' in fr.data, \
            "Response must have 'models' key"
        assert isinstance(fr.data['models'], list), \
            "'models' must be a list"

    def test_models_all_nine_present(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models'), fr)
        names = set(fr.data['models'])
        expected = {'SVM', 'LR', 'Tree', 'RF', 'KNN', 'MLP', 'GB', 'ET', 'AB', 'NB'}
        assert names == expected, \
            f"Expected models {expected}, got {names}"

    def test_models_svm_detail(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models/SVM'), fr)
        assert fr.status is None, \
            f"Expected success for SVM, got {fr.status}"
        assert fr.data['name'] == 'SVM'
        assert fr.data['complexity'] == 'medium'
        assert 'parameters' in fr.data
        assert 'defaults' in fr.data
        assert 'scenarios' in fr.data
        assert 'presets' in fr.data
        assert 'C' in fr.data['parameters']
        assert 'gamma' in fr.data['parameters']

    def test_models_nb_has_no_parameters(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models/NB'), fr)
        assert fr.status is None
        assert fr.data['name'] == 'NB'
        assert fr.data['parameters'] == {}
        assert fr.data['defaults'] == {}

    def test_models_unknown_returns_404(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models/UNKNOWN_MODEL_XYZ'), fr)
        assert fr.status == 404, \
            f"Unknown model must return 404, got {fr.status}"
        assert 'error' in fr.data
        assert 'UNKNOWN_MODEL_XYZ' in fr.data['error']
        assert 'available' in fr.data

    def test_models_have_required_fields(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models'), fr)
        # test all individual models
        for model_name in fr.data['models']:
            fr = FakeRes()
            handle(FakeReq(f'/api/models/{model_name}'), fr)
            assert fr.status is None, \
                f"Model '{model_name}' must succeed, got {fr.status}"
            required = {'name', 'full_name', 'description', 'complexity',
                        'parameters', 'defaults', 'scenarios', 'presets'}
            missing = required - set(fr.data.keys())
            assert not missing, \
                f"Model '{model_name}' missing: {missing}"

    def test_models_presets_have_balanced_high_accuracy_lightweight(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models'), fr)
        preset_keys = {'balanced', 'high_accuracy', 'lightweight'}
        for model_name in fr.data['models']:
            fr = FakeRes()
            handle(FakeReq(f'/api/models/{model_name}'), fr)
            missing = preset_keys - set(fr.data.get('presets', {}).keys())
            assert not missing, \
                f"Model '{model_name}' presets missing: {missing}"

    def test_models_complexity_labels_valid(self):
        from api.models import handle

        fr = FakeRes()
        handle(FakeReq('/api/models'), fr)
        valid = {'low', 'medium', 'high'}
        for model_name in fr.data['models']:
            fr = FakeRes()
            handle(FakeReq(f'/api/models/{model_name}'), fr)
            assert fr.data['complexity'] in valid, \
                f"Model '{model_name}' complexity must be in {valid}"


# ─────────────────────────────────────────────────────────────────────────────
# Flask integration — web/server.py routes
# NOTE: Flask is not installed in the test environment; Flask integration
# tests are manual smoke tests. Core contract is tested via Vercel handlers.
# ─────────────────────────────────────────────────────────────────────────────

import pytest

class TestWebServerAPIRoutes:
    """Test Flask routes in web/server.py for the new endpoints.
    
    Skipped when Flask is not available; run manually with:
    $ python web/server.py  # then: curl localhost:5000/api/models/SVM
    """

    @pytest.mark.skip(reason="Flask not installed in test env — manual smoke test")
    def test_flask_app_has_models_route(self):
        from web.server import app
        client = app.test_client()
        rv = client.get('/api/models/SVM')
        assert rv.status_code == 200, f"/api/models/SVM → {rv.status_code}"
        assert rv.get_json()['name'] == 'SVM'

    @pytest.mark.skip(reason="Flask not installed in test env — manual smoke test")
    def test_flask_app_has_datasets_route(self):
        from web.server import app
        client = app.test_client()
        rv = client.get('/api/datasets')
        assert rv.status_code == 200, f"/api/datasets → {rv.status_code}"
        data = rv.get_json()
        assert 'datasets' in data and 'count' in data

    @pytest.mark.skip(reason="Flask not installed in test env — manual smoke test")
    def test_flask_unknown_model_returns_404(self):
        from web.server import app
        client = app.test_client()
        rv = client.get('/api/models/BOGUS_MODEL')
        assert rv.status_code == 404

    @pytest.mark.skip(reason="Flask not installed in test env — manual smoke test")
    def test_flask_datasets_returns_all_eight(self):
        from web.server import app
        client = app.test_client()
        rv = client.get('/api/datasets')
        names = {d['name'] for d in rv.get_json()['datasets']}
        expected = {
            'circles', 'moons', 'blobs', 'xor', 's_curve',
            'swiss_roll', 'classification_2blobs', 'classification_concentric',
        }
        assert names == expected


# ─────────────────────────────────────────────────────────────────────────────
# API module structure
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIModuleStructureV10:
    """Verify api/ module structure for v10 endpoints."""

    def test_models_has_handle(self):
        from api import models
        assert hasattr(models, 'handle'), \
            "api/models.py must export 'handle' for Vercel"
        assert callable(models.handle)

    def test_datasets_has_handle(self):
        from api import datasets
        assert hasattr(datasets, 'handle'), \
            "api/datasets.py must export 'handle' for Vercel"
        assert callable(datasets.handle)
