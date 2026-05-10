"""
Vercel serverless function: /api/train
Exposes the ML training endpoint for the interactive web interface.
"""

import matplotlib
matplotlib.use('Agg')  # headless backend for serverless
import matplotlib.pyplot as plt

import time
import numpy as np

from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import RandomForestClassifier
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.model_selection import train_test_split


def make_circles(n, noise, seed):
    from sklearn.datasets import make_circles as sk_circles
    X, y = sk_circles(n_samples=n, noise=noise, random_state=seed, factor=0.5)
    return X, y


def make_moons(n, noise, seed):
    from sklearn.datasets import make_moons as sk_moons
    X, y = sk_moons(n_samples=n, noise=noise, random_state=seed)
    return X, y


def make_blobs(n, seed):
    from sklearn.datasets import make_blobs
    X, y = make_blobs(n_samples=n, centers=3, random_state=seed, cluster_std=1.5)
    mask = y < 2
    return X[mask], y[mask]


def make_xor(n, noise, seed):
    np.random.seed(seed)
    X = np.random.randn(n, 2)
    y = ((X[:, 0] > 0) ^ (X[:, 1] > 0)).astype(int)
    X += np.random.randn(n, 2) * noise
    return X, y


DATASET_GENERATORS = {
    'circles': lambda n, noise, seed: make_circles(n, noise, seed),
    'moons':    lambda n, noise, seed: make_moons(n, noise, seed),
    'blobs':    lambda n, noise, seed: make_blobs(n, seed),
    'xor':      lambda n, noise, seed: make_xor(n, noise, seed),
}


def build_model(model_name, params):
    factories = {
        'SVM':  lambda: SVC(**params, random_state=42),
        'LR':   lambda: LogisticRegression(**params, random_state=42, max_iter=1000),
        'Tree': lambda: DecisionTreeClassifier(**params, random_state=42),
        'RF':   lambda: RandomForestClassifier(**params, random_state=42),
        'KNN':  lambda: KNeighborsClassifier(**params),
        'MLP':  lambda: MLPClassifier(**params, random_state=42, max_iter=2000),
    }
    if model_name not in factories:
        raise ValueError(f'Unknown model: {model_name}')
    return factories[model_name]()


def slider_to_params(model_name, p1, p2):
    n1 = p1 / 100.0
    n2 = p2 / 100.0

    if model_name == 'SVM':
        C = 10 ** (n1 * 3 - 1)
        gamma_opts = ['scale', 'auto', 0.01, 0.1, 1.0, 10.0]
        gamma = gamma_opts[min(int(n2 * 5), 5)]
        return {'kernel': 'rbf', 'C': C, 'gamma': gamma}
    elif model_name == 'LR':
        C = 10 ** (n1 * 3 - 1)
        return {'C': C}
    elif model_name == 'Tree':
        max_depth = max(1, int(n1 * 20))
        min_samples = int(n2 * 20) + 2
        return {'max_depth': max_depth, 'min_samples_split': min_samples}
    elif model_name == 'RF':
        n_estimators = int(n1 * 190 + 10)
        max_depth = max(1, int(n2 * 19))
        return {'n_estimators': n_estimators, 'max_depth': max_depth}
    elif model_name == 'KNN':
        k = max(1, int(n1 * 49 + 1))
        return {'n_neighbors': k}
    elif model_name == 'MLP':
        hidden = max(10, int(n1 * 190 + 10))
        alpha = n2 * 0.1
        return {'hidden_layer_sizes': (hidden,), 'alpha': alpha}
    return {}


def compute_boundary_grid(model, X_train, resolution=40):
    x_min, x_max = X_train[:, 0].min() - 0.5, X_train[:, 0].max() + 0.5
    y_min, y_max = X_train[:, 1].min() - 0.5, X_train[:, 1].max() + 0.5
    xx, yy = np.meshgrid(
        np.linspace(x_min, x_max, resolution),
        np.linspace(y_min, y_max, resolution)
    )
    Z = model.predict(np.c_[xx.ravel(), yy.ravel()])
    Z = Z.reshape(xx.shape)
    return xx, yy, Z.astype(float)


def get_model_info_dict(model, model_name):
    info = {}
    if model_name == 'SVM':
        info['Support Vectors'] = int(len(model.support_vectors_))
        info['Kernel'] = 'RBF'
    elif model_name == 'Tree':
        info['Tree Depth'] = model.get_depth()
        info['Leaves'] = model.get_n_leaves()
    elif model_name == 'RF':
        info['Num Trees'] = len(model.estimators_)
        info['Max Depth'] = max(e.get_depth() for e in model.estimators_)
    elif model_name == 'KNN':
        info['K Value'] = model.n_neighbors
        info['Algorithm'] = 'auto'
    elif model_name == 'MLP':
        info['Layers'] = len(model.hidden_layer_sizes)
        info['Layer Sizes'] = str(model.hidden_layer_sizes)
    elif model_name == 'LR':
        info['Converged'] = model.n_iter_[0] if hasattr(model, 'n_iter_') else '?'
    return info


def handle(req, res):
    """Vercel Python serverless handler."""
    # Error code constants for client-facing responses
    ERR_DATASET_UNKNOWN = 'DATASET_UNKNOWN'
    ERR_MODEL_UNKNOWN  = 'MODEL_UNKNOWN'
    ERR_TRAINING_ERROR = 'TRAINING_ERROR'
    ERR_VALIDATION     = 'VALIDATION_ERROR'

    try:
        body = req.get_json()
        model_name = body.get('model', 'SVM')
        dataset_name = body.get('dataset', 'circles')
        p1 = float(body.get('p1', 50))
        p2 = float(body.get('p2', 50))

        if dataset_name not in DATASET_GENERATORS:
            res.status = 400
            res.json({'error': f'Unknown dataset: {dataset_name}', 'code': ERR_DATASET_UNKNOWN})
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
    except ValueError as e:
        # Validation errors (e.g., unknown model) — safe to expose message
        res.status = 400
        res.json({'error': str(e), 'code': ERR_VALIDATION})
    except Exception as e:
        # Unexpected errors — message is sanitized; no internal paths leaked
        res.status = 500
        res.json({'error': 'Internal training error', 'code': ERR_TRAINING_ERROR})
