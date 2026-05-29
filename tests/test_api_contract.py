"""
tests/test_api_contract.py — Enhanced API contract tests

Covers the serverless function contracts for /api/health and /api/train.
These test the Vercel serverless entrypoints in api/health.py and api/train.py.

Contract expectations:
- /api/health: returns {status: 'ok'} with no error handling needed
- /api/train: accepts {model, dataset, p1, p2}; returns accuracy + boundary data or error
"""

import pytest
import sys
import os

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

class FakeReq:
    """Fake Vercel req object for serverless function testing."""
    def __init__(self, body: dict):
        self._body = body

    def get_json(self):
        return self._body


class FakeRes:
    """Fake Vercel res object for serverless function testing."""
    def __init__(self):
        self.status = None
        self.data = None

    def json(self, d):
        self.data = d


# ─────────────────────────────────────────────────────────────────────────────
# /api/health — Contract Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIHealth:
    """Test /api/health serverless function contract."""

    def test_health_returns_ok(self):
        """Health endpoint returns {'status': 'ok'} per P3 spec."""
        from api.health import handle

        fr = FakeRes()
        handle(FakeReq({}), fr)
        assert fr.data == {'status': 'ok'}, \
            "Health must return exact {status: 'ok'}"

    def test_health_always_ok(self):
        """Health must always return ok regardless of request body."""
        from api.health import handle

        for body in [{}, None, {"anything": True}]:
            fr = FakeRes()
            handle(FakeReq(body), fr)
            assert fr.data == {'status': 'ok'}, \
                f"Health must return ok for body={body}"


# ─────────────────────────────────────────────────────────────────────────────
# /api/train — Contract Tests
# ─────────────────────────────────────────────────────────────────────────────

class TestAPITrain:
    """Test /api/train serverless function contract."""

    def test_train_unknown_dataset_returns_400(self):
        """Unknown dataset → HTTP 400 with error message."""
        from api.train import handle

        fr = FakeRes()
        handle(FakeReq({
            'dataset': 'nonexistent_dataset',
            'model': 'SVM',
            'p1': 50,
            'p2': 50,
        }), fr)
        assert fr.status == 400, \
            f"Unknown dataset must return 400, got {fr.status}"
        assert 'error' in fr.data, \
            "Error response must contain 'error' key"
        assert 'nonexistent_dataset' in fr.data['error'], \
            "Error message should mention the invalid dataset name"

    def test_train_unknown_model_returns_500(self):
        """Unknown model type → HTTP 500 with error message."""
        from api.train import handle

        fr = FakeRes()
        handle(FakeReq({
            'dataset': 'circles',
            'model': 'UNKNOWN_MODEL_XYZ',
            'p1': 50,
            'p2': 50,
        }), fr)
        # build_model raises ValueError for unknown models → caught by except → 500
        assert fr.status == 500, \
            f"Unknown model must return 500, got {fr.status}"
        assert 'error' in fr.data, \
            "Error response must contain 'error' key"
        assert 'UNKNOWN_MODEL_XYZ' in fr.data['error'], \
            "Error message should mention the invalid model name"

    def test_train_valid_call_returns_fields(self):
        """Valid request returns all required response fields."""
        from api.train import handle

        fr = FakeRes()
        handle(FakeReq({
            'model': 'SVM',
            'dataset': 'circles',
            'p1': 50,
            'p2': 50,
        }), fr)

        assert fr.status is None, \
            "Valid call should not set error status (success)"
        assert isinstance(fr.data, dict), \
            "Response data must be a dict"

        required_fields = [
            'accuracy', 'train_time', 'boundary_grid',
            'train_points', 'bounds', 'model_info',
            'model', 'dataset', 'params',
        ]
        for field in required_fields:
            assert field in fr.data, \
                f"Response must contain '{field}' field"

        # Type checks
        assert isinstance(fr.data['accuracy'], (int, float)), \
            "accuracy must be numeric"
        assert 0.0 <= fr.data['accuracy'] <= 1.0, \
            "accuracy must be in [0, 1]"
        assert fr.data['train_time'] >= 0, \
            "train_time must be non-negative"
        assert isinstance(fr.data['boundary_grid'], list), \
            "boundary_grid must be a list"

        # train_points shape
        tp = fr.data['train_points']
        assert all(k in tp for k in ('xs', 'ys', 'labels')), \
            "train_points must have xs, ys, labels"

    def test_train_missing_optional_p1_p2(self):
        """p1/p2 are optional; missing them uses defaults (50, 50)."""
        from api.train import handle

        fr = FakeRes()
        handle(FakeReq({
            'model': 'SVM',
            'dataset': 'circles',
        }), fr)

        assert fr.status is None, \
            "Missing p1/p2 should use defaults and succeed"
        assert 'accuracy' in fr.data, \
            "Valid call without p1/p2 must succeed"

    def test_train_all_models_work(self):
        """All supported model types produce valid responses."""
        from api.train import handle

        models = ['SVM', 'LR', 'Tree', 'RF', 'KNN', 'MLP', 'NB', 'GB', 'ET', 'AB']
        datasets = ['circles', 'moons', 'blobs', 'xor']

        for model in models:
            for dataset in datasets[:2]:  # smoke test — first 2 datasets
                fr = FakeRes()
                handle(FakeReq({
                    'model': model,
                    'dataset': dataset,
                    'p1': 50,
                    'p2': 50,
                }), fr)
                assert fr.status is None or fr.status == 200, \
                    f"{model}/{dataset} must succeed, got {fr.status}"
                assert 'accuracy' in fr.data, \
                    f"{model}/{dataset} must return accuracy"

    def test_train_all_datasets_work(self):
        """All dataset types work with SVM."""
        from api.train import handle

        datasets = ['circles', 'moons', 'blobs', 'xor', 's_curve']
        for dataset in datasets:
            fr = FakeRes()
            handle(FakeReq({
                'model': 'SVM',
                'dataset': dataset,
                'p1': 50,
                'p2': 50,
            }), fr)
            assert fr.status is None, \
                f"dataset={dataset} must succeed, got {fr.status}"
            assert 'accuracy' in fr.data, \
                f"dataset={dataset} must return accuracy"

    def test_train_p1_p2_affects_model_params(self):
        """Different p1/p2 values produce different model params."""
        from api.train import handle

        fr_low = FakeRes()
        handle(FakeReq({
            'model': 'SVM', 'dataset': 'circles',
            'p1': 10, 'p2': 10,  # low
        }), fr_low)

        fr_high = FakeRes()
        handle(FakeReq({
            'model': 'SVM', 'dataset': 'circles',
            'p1': 90, 'p2': 90,  # high
        }), fr_high)

        # p1/p2 should map to different C/gamma → different params
        assert fr_low.data['params'] != fr_high.data['params'], \
            "Different p1/p2 must produce different model params"


# ─────────────────────────────────────────────────────────────────────────────
# Cross-module consistency
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIContract:
    """Contract consistency between main.py and api/train.py."""

    def test_train_model_signature_consistency(self):
        """
        train_model(model_type, params, X, y) must be consistent
        across main.py and the train serverless function.
        """
        from main import train_model, generate_dataset

        X, y = generate_dataset("circles", n_samples=100, seed=42)
        model, train_time = train_model(
            "SVM", {"C": 1.0, "kernel": "rbf"}, X, y
        )
        assert train_time >= 0
        assert 0.0 <= model.score(X, y) <= 1.0

    def test_api_train_uses_same_build_model(self):
        """api/train.py must use the same build_model as main.py/core/train_utils."""
        from core.train_utils import build_model
        from api.train import build_model as api_build_model

        # Both must produce SVC with same params
        m1 = build_model("SVM", {"C": 1.0, "kernel": "rbf"})
        m2 = api_build_model("SVM", {"C": 1.0, "kernel": "rbf"})

        assert type(m1) == type(m2), \
            "api/train.py and core/train_utils.py must use same build_model"


# ─────────────────────────────────────────────────────────────────────────────
# API module structure
# ─────────────────────────────────────────────────────────────────────────────

class TestAPIModuleStructure:
    """Verify api/ module has expected structure for Vercel deployment."""

    def test_health_has_handle(self):
        """api/health.py must export a 'handle' function."""
        from api import health
        assert hasattr(health, 'handle'), \
            "api/health.py must export 'handle' for Vercel"
        assert callable(health.handle), \
            "health.handle must be callable"

    def test_train_has_handle(self):
        """api/train.py must export a 'handle' function."""
        from api import train
        assert hasattr(train, 'handle'), \
            "api/train.py must export 'handle' for Vercel"
        assert callable(train.handle), \
            "train.handle must be callable"

    def test_train_exports_reusable_functions(self):
        """api/train.py should export reusable ML functions for non-Vercel use."""
        from api import train
        # These are imported from core/train_utils.py but re-exported via api/train
        for name in ['build_model', 'slider_to_params', 'get_model_info_dict']:
            assert hasattr(train, name), \
                f"api/train.py must export '{name}' for programmatic use"

    def test_api_train_no_error_traceback_leak(self):
        """API errors must not expose Python tracebacks in response."""
        from api.train import handle

        class FakeReq:
            def get_json(self):
                return {'dataset': 'circles', 'model': 'UNKNOWN_MODEL', 'p1': 50, 'p2': 50}

        fr = FakeRes()
        handle(FakeReq(), fr)
        # Error message should be clean, not a traceback
        assert fr.status == 500
        assert isinstance(fr.data['error'], str)
        assert 'Traceback' not in fr.data['error'], \
            "Error responses must not contain Python tracebacks"