#!/usr/bin/env python3
"""
Flask server for ML Decision Boundary Web Interface
Runs real sklearn training and returns decision boundary data
"""

import matplotlib
matplotlib.use('Agg')  # headless backend for server environments
import matplotlib.pyplot as plt

import json
import uuid
import datetime
import time
import numpy as np
from flask import Flask, request, jsonify, send_from_directory
from sklearn.model_selection import train_test_split

from core.datasets import DATASET_GENERATORS
from core.train_utils import (
    build_model,
    slider_to_params,
    compute_boundary_grid,
    get_model_info_dict,
)
from core.experiment_history import log_experiment

app = Flask(__name__, static_folder='.', static_url_path='')


@app.route('/')
def index():
    return send_from_directory('.', 'index.html')


@app.route('/train', methods=['POST'])
def train():
    try:
        body = request.get_json()
        model_name = body.get('model', 'SVM')
        dataset_name = body.get('dataset', 'circles')
        p1 = float(body.get('p1', 50))
        p2 = float(body.get('p2', 50))
        n_samples = int(body.get('n_samples', 500))

        if dataset_name not in DATASET_GENERATORS:
            return jsonify({'error': f'Unknown dataset: {dataset_name}'}), 400

        X, y = DATASET_GENERATORS[dataset_name](n_samples, 0.3, seed=42)
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

        try:
            log_experiment({
                "model": model_name,
                "dataset": dataset_name,
                "accuracy": accuracy,
                "train_time": train_time,
                "params": params,
                "n_samples": n_samples,
            })
        except Exception:
            pass  # experiment logging failure must NOT break the training response

        return jsonify({
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
        return jsonify({'error': str(e)}), 500


@app.route('/api/models/<model_name>', methods=['GET'])
def api_models(model_name):
    """Return model metadata catalogue entry."""
    from api.models import MODEL_CATALOGUE
    if model_name not in MODEL_CATALOGUE:
        return jsonify({
            'error': f"Unknown model: '{model_name}'",
            'available': list(MODEL_CATALOGUE.keys()),
        }), 404
    return jsonify(MODEL_CATALOGUE[model_name])


@app.route('/api/datasets', methods=['GET'])
def api_datasets():
    """Return dataset catalogue."""
    from api.datasets import DATASET_CATALOGUE
    return jsonify({
        'datasets': DATASET_CATALOGUE,
        'count': len(DATASET_CATALOGUE),
    })


@app.route('/api/predict/batch', methods=['POST'])
def api_predict_batch():
    """Batch prediction: POST /api/predict/batch with JSON body."""
    try:
        body = request.get_json()
    except Exception:
        return jsonify({'error': 'Invalid JSON body'}), 400

    model_name = body.get('model')
    dataset_name = body.get('dataset')
    points = body.get('points')

    if not model_name:
        return jsonify({'error': 'Missing required field: model'}), 400
    if not dataset_name:
        return jsonify({'error': 'Missing required field: dataset'}), 400
    if points is None:
        return jsonify({'error': 'Missing required field: points'}), 400

    if not isinstance(points, list) or len(points) == 0:
        return jsonify({'error': 'Field "points" must be a non-empty array'}), 400

    parsed = []
    for i, pt in enumerate(points):
        if not isinstance(pt, (list, tuple)) or len(pt) != 2:
            return jsonify({
                'error': f'points[{i}] must be a [x, y] pair, got: {pt!r}'
            }), 400
        try:
            parsed.append([float(pt[0]), float(pt[1])])
        except (TypeError, ValueError):
            return jsonify({
                'error': f'points[{i}] values must be numeric, got: {pt!r}'
            }), 400

    if dataset_name not in DATASET_GENERATORS:
        return jsonify({'error': f'Unknown dataset: {dataset_name}'}), 400

    p1 = float(body.get('p1', 50))
    p2 = float(body.get('p2', 50))

    try:
        params = slider_to_params(model_name, p1, p2)
        model = build_model(model_name, params)
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

    X, y = DATASET_GENERATORS[dataset_name](500, 0.3, seed=42)
    model.fit(X, y)

    import numpy as np
    X_pts = np.array(parsed)
    predictions = model.predict(X_pts).tolist()

    return jsonify({
        'model': model_name,
        'dataset': dataset_name,
        'params': params,
        'predictions': predictions,
        'count': len(predictions),
    })


@app.route('/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok'})


@app.route('/api/experiments', methods=['GET'])
def api_experiments():
    """Return experiment history from experiments.jsonl."""
    from core.experiment_history import get_history
    limit = request.args.get('limit', 50, type=int)
    history = get_history(limit=limit)
    return jsonify({
        "experiments": history,
        "count": len(history),
    })


@app.route('/api/experiments/clear', methods=['POST'])
def api_experiments_clear():
    """Clear experiment history (dev use only)."""
    from core.experiment_history import clear_history
    clear_history()
    return jsonify({"status": "cleared"})


if __name__ == '__main__':
    print("🚀 Starting ML Decision Boundary server...")
    print("   Open http://localhost:5000 in your browser")
    app.run(host='0.0.0.0', port=5000, debug=False)