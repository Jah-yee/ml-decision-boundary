"""Vercel serverless function: /api/predict/batch

Batch prediction endpoint: trains a model on the specified dataset and
returns predictions for an array of 2D input points.

POST body (JSON):
    {
        "model":     "SVM",          # required; model name from MODEL_CATALOGUE
        "dataset":   "circles",      # required; dataset name from DATASET_CATALOGUE
        "p1":        50,             # optional; slider 0-100 → model param 1 (default 50)
        "p2":        50,             # optional; slider 0-100 → model param 2 (default 50)
        "points": [[0.1, 0.2], ...] # required; array of [x, y] points to classify
    }

Returns 200:
    {
        "model":     "SVM",
        "dataset":   "circles",
        "params":    {"kernel": "rbf", "C": 1.0, "gamma": "scale"},
        "predictions": [1, 0, 1, ...],   # one label per input point
        "count":     3,
    }

Returns 400 on validation errors, 500 on internal errors.

Example:
    >>> curl -X POST https://your-app.vercel.app/api/predict/batch \\
           -H "Content-Type: application/json" \\
           -d '{"model":"SVM","dataset":"circles","points":[[0,0],[1,1]]}'
    {"model": "SVM", "dataset": "circles", "predictions": [1, 0], "count": 2, ...}
"""

from core.datasets import DATASET_GENERATORS
from core.train_utils import build_model, slider_to_params
from core.error_messages import E1007_UNKNOWN_DATASET, format_error


def handle(req, res):
    """Vercel serverless handler — POST /api/predict/batch."""
    try:
        body = req.get_json()
    except Exception:
        res.status = 400
        res.json({'error': 'Invalid JSON body'})
        return

    # ── Required fields ────────────────────────────────────────────────
    model_name = body.get('model')
    dataset_name = body.get('dataset')
    points = body.get('points')

    if not model_name:
        res.status = 400
        res.json({'error': 'Missing required field: model'})
        return
    if not dataset_name:
        res.status = 400
        res.json({'error': 'Missing required field: dataset'})
        return
    if points is None:
        res.status = 400
        res.json({'error': 'Missing required field: points'})
        return

    # ── Validate points ──────────────────────────────────────────────────
    if not isinstance(points, list):
        res.status = 400
        res.json({'error': 'Field "points" must be an array'})
        return
    if len(points) == 0:
        res.status = 400
        res.json({'error': 'Field "points" must not be empty'})
        return

    parsed = []
    for i, pt in enumerate(points):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            res.status = 400
            res.json({
                'error': f'points[{i}] must be a [x, y] pair, got: {pt!r}'
            })
            return
        try:
            x, y = float(pt[0]), float(pt[1])
        except (TypeError, ValueError):
            res.status = 400
            res.json({
                'error': f'points[{i}] values must be numeric, got: {pt!r}'
            })
            return
        parsed.append([x, y])

    # ── Validate dataset ──────────────────────────────────────────────────
    if dataset_name not in DATASET_GENERATORS:
        res.status = 400
        res.json({'error': format_error(E1007_UNKNOWN_DATASET, name=dataset_name)})
        return

    # ── Train model ───────────────────────────────────────────────────────
    p1 = float(body.get('p1', 50))
    p2 = float(body.get('p2', 50))

    try:
        params = slider_to_params(model_name, p1, p2)
        model = build_model(model_name, params)
    except ValueError as e:
        res.status = 400
        res.json({'error': str(e)})
        return

    # Generate training data
    X, y = DATASET_GENERATORS[dataset_name](500, 0.3, seed=42)
    model.fit(X, y)

    # Batch predict
    import numpy as np
    X_pts = np.array(parsed)
    predictions = model.predict(X_pts).tolist()

    res.json({
        'model': model_name,
        'dataset': dataset_name,
        'params': params,
        'predictions': predictions,
        'count': len(predictions),
    })
