"""
Tests for POST /api/predict/batch endpoint via serverless contract pattern.
Uses FakeReq/FakeRes to test api/predict.py without Flask dependency.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class FakeReq:
    """Fake Vercel req object for serverless function testing."""
    def __init__(self, body: dict, url: str = '/api/predict/batch'):
        self._body = body
        self.url = url

    def get_json(self):
        return self._body


class FakeRes:
    """Fake Vercel res object for serverless function testing."""
    def __init__(self):
        self.status = None
        self.data = None

    def json(self, d):
        self.data = d


# ─── Happy path ──────────────────────────────────────────────────────────────

def test_batch_predict_basic():
    """Basic smoke: circles + SVM, 3 points, expect 3 predictions."""
    from api.predict import handle

    fr = FakeReq({
        'model': 'SVM',
        'dataset': 'circles',
        'points': [[0.0, 0.0], [1.0, 0.0], [0.5, 0.5]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status is None or res.status == 200
    data = res.data
    assert data['model'] == 'SVM'
    assert data['dataset'] == 'circles'
    assert 'params' in data
    assert isinstance(data['predictions'], list)
    assert len(data['predictions']) == 3
    assert data['count'] == 3
    for p in data['predictions']:
        assert p in (0, 1), f"Unexpected prediction: {p}"


def test_batch_predict_all_models():
    """All model names should accept a batch request without error."""
    from api.predict import handle

    models = ['SVM', 'LR', 'Tree', 'RF', 'KNN', 'MLP', 'GB', 'ET', 'AB', 'NB']
    for model in models:
        fr = FakeReq({
            'model': model,
            'dataset': 'circles',
            'points': [[0.0, 0.0], [0.5, 0.5]],
        })
        res = FakeRes()
        handle(fr, res)
        assert res.status is None or res.status == 200, \
            f"Failed for model={model}: {res.data}"


def test_batch_predict_all_datasets():
    """All dataset names should accept a batch request without error."""
    from api.predict import handle

    datasets = [
        'circles', 'moons', 'blobs', 'xor', 's_curve',
        'swiss_roll', 'classification_2blobs', 'classification_concentric',
    ]
    for ds in datasets:
        fr = FakeReq({
            'model': 'SVM',
            'dataset': ds,
            'points': [[0.0, 0.0], [0.5, 0.5]],
        })
        res = FakeRes()
        handle(fr, res)
        assert res.status is None or res.status == 200, \
            f"Failed for dataset={ds}: {res.data}"


def test_batch_predict_with_slider_params():
    """p1/p2 should influence the response (params key must be non-empty)."""
    from api.predict import handle

    fr = FakeReq({
        'model': 'SVM',
        'dataset': 'circles',
        'p1': 80,
        'p2': 20,
        'points': [[0.0, 0.0]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status is None or res.status == 200
    assert res.data['params']


def test_batch_predict_single_point():
    """Single-point batch (len=1) must work."""
    from api.predict import handle

    fr = FakeReq({
        'model': 'LR',
        'dataset': 'blobs',
        'points': [[0.5, 0.5]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status is None or res.status == 200
    assert res.data['count'] == 1
    assert len(res.data['predictions']) == 1


# ─── Validation errors ───────────────────────────────────────────────────────

def test_batch_predict_missing_model():
    from api.predict import handle

    fr = FakeReq({'dataset': 'circles', 'points': [[0, 0]]})
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'model' in res.data['error'].lower()


def test_batch_predict_missing_dataset():
    from api.predict import handle

    fr = FakeReq({'model': 'SVM', 'points': [[0, 0]]})
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'dataset' in res.data['error'].lower()


def test_batch_predict_missing_points():
    from api.predict import handle

    fr = FakeReq({'model': 'SVM', 'dataset': 'circles'})
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'points' in res.data['error'].lower()


def test_batch_predict_empty_points():
    from api.predict import handle

    fr = FakeReq({'model': 'SVM', 'dataset': 'circles', 'points': []})
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'empty' in res.data['error'].lower()


def test_batch_predict_point_wrong_length():
    from api.predict import handle

    fr = FakeReq({
        'model': 'SVM',
        'dataset': 'circles',
        'points': [[0, 0, 0]],  # 3 elements instead of 2
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'pair' in res.data['error'].lower()


def test_batch_predict_point_non_numeric():
    from api.predict import handle

    fr = FakeReq({
        'model': 'SVM',
        'dataset': 'circles',
        'points': [["a", "b"]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'numeric' in res.data['error'].lower()


def test_batch_predict_unknown_model():
    from api.predict import handle

    fr = FakeReq({
        'model': 'NonExistentModel',
        'dataset': 'circles',
        'points': [[0, 0]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'error' in res.data


def test_batch_predict_unknown_dataset():
    from api.predict import handle

    fr = FakeReq({
        'model': 'SVM',
        'dataset': 'nonexistent_dataset',
        'points': [[0, 0]],
    })
    res = FakeRes()
    handle(fr, res)
    assert res.status == 400
    assert 'Unknown dataset' in res.data['error']


def test_batch_predict_invalid_json():
    """Invalid JSON body should return 400."""
    from api.predict import handle

    class BadFakeReq:
        def get_json(self):
            raise ValueError("not JSON")

    res = FakeRes()
    handle(BadFakeReq(), res)
    assert res.status == 400
    assert 'Invalid JSON' in res.data['error']
