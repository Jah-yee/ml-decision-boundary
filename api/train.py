"""
Vercel serverless function: /api/train
Exposes the ML training endpoint for the interactive web interface.
"""

import time
import numpy as np

from sklearn.model_selection import train_test_split

from core.datasets import DATASET_GENERATORS
from core.train_utils import (
    build_model,
    slider_to_params,
    compute_boundary_grid,
    get_model_info_dict,
)
from core.error_messages import E1007_UNKNOWN_DATASET, format_error


def handle(req, res):
    """Vercel Python serverless handler."""
    try:
        body = req.get_json()
        model_name = body.get('model', 'SVM')
        dataset_name = body.get('dataset', 'circles')
        p1 = float(body.get('p1', 50))
        p2 = float(body.get('p2', 50))

        if dataset_name not in DATASET_GENERATORS:
            res.status = 400
            res.json({'error': format_error(E1007_UNKNOWN_DATASET, name=dataset_name)})
            return

        X, y = DATASET_GENERATORS[dataset_name](500, 0.3, seed=42)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42
        )

        params = slider_to_params(model_name, p1, p2)
        model = build_model(model_name, params)

        t0 = time.perf_counter()
        model.fit(X_train, y_train)
        train_time = time.perf_counter() - t0

        accuracy = float(model.score(X_test, y_test))
        xx, yy, Z = compute_boundary_grid(model, X_train, resolution=40)

        res.json({
            'accuracy': accuracy,
            'train_time': train_time,
            'boundary_grid': Z.tolist(),
            'train_points': {
                'xs': X_train[:, 0].tolist(),
                'ys': X_train[:, 1].tolist(),
                'labels': y_train.tolist(),
            },
            'bounds': {
                'x_min': float(xx.min()), 'x_max': float(xx.max()),
                'y_min': float(yy.min()), 'y_max': float(yy.max()),
            },
            'model_info': get_model_info_dict(model, model_name),
            'model': model_name,
            'dataset': dataset_name,
            'params': params,
        })
    except Exception as e:
        res.status = 500
        res.json({'error': str(e)})