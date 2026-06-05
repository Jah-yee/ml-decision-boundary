"""
core/train_utils.py — Shared ML training utilities

Dataset-agnostic helpers: build_model, slider_to_params,
compute_boundary_grid, get_model_info_dict.
All live here once; api/train.py, web/server.py, main.py import from here.
"""

import numpy as np

from sklearn.svm import SVC
from sklearn.linear_model import LogisticRegression
from sklearn.tree import DecisionTreeClassifier
from sklearn.ensemble import (
    RandomForestClassifier,
    GradientBoostingClassifier,
    ExtraTreesClassifier,
    AdaBoostClassifier,
)
from sklearn.neighbors import KNeighborsClassifier
from sklearn.neural_network import MLPClassifier
from sklearn.naive_bayes import GaussianNB


def build_model(model_name, params):
    """Factory: build an sklearn estimator from name + keyword params.

    Plugin-aware: first checks core/plugins/models/ for a registered plugin.
    Falls back to builtin sklearn models if no plugin found.
    Raises ValueError if model_name is unknown to both plugin system and builtins.
    """
    # Try plugin system first
    try:
        from core.plugins.registry import get_plugin_model
        plugin = get_plugin_model(model_name)
        if plugin is not None:
            return plugin.build(**params)
    except Exception:
        pass  # Fall through to builtins

    # Builtin sklearn factories
    factories = {
        'SVM':  lambda: SVC(**params, random_state=42),
        'LR':   lambda: LogisticRegression(**params, random_state=42, max_iter=1000),
        'Tree': lambda: DecisionTreeClassifier(**params, random_state=42),
        'RF':   lambda: RandomForestClassifier(**params, random_state=42),
        'KNN':  lambda: KNeighborsClassifier(**params),
        'MLP':  lambda: MLPClassifier(**params, random_state=42, max_iter=500),
        'NB':   lambda: GaussianNB(**params),
        'GB':   lambda: GradientBoostingClassifier(**params, random_state=42),
        'ET':   lambda: ExtraTreesClassifier(**params, random_state=42),
        'AB':   lambda: AdaBoostClassifier(**params, random_state=42, algorithm='SAMME'),
    }
    if model_name not in factories:
        # Provide helpful error with available options
        try:
            from core.plugins.registry import discover_plugins
            plugins = discover_plugins()
            builtin_list = list(factories.keys())
            plugin_list = list(plugins.keys())
            all_options = builtin_list + plugin_list
        except Exception:
            all_options = list(factories.keys())
        raise ValueError(
            f"Unknown model: '{model_name}'. "
            f"Available models: {', '.join(all_options)}. "
            f"Run with --list-models to see all."
        )
    return factories[model_name]()


def slider_to_params(model_name, p1, p2):
    """Convert 0-100 slider values to model keyword arguments."""
    n1 = p1 / 100.0
    n2 = p2 / 100.0

    if model_name == 'SVM':
        C = 10 ** (n1 * 3 - 1)          # 0.1 → 100
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

    elif model_name == 'GB':
        n_estimators = int(n1 * 190 + 10)
        max_depth = max(1, int(n2 * 19))
        learning_rate = 0.05 + n2 * 0.15
        return {'n_estimators': n_estimators, 'max_depth': max_depth, 'learning_rate': learning_rate}

    elif model_name == 'ET':
        n_estimators = int(n1 * 190 + 10)
        max_depth = max(1, int(n2 * 19))
        return {'n_estimators': n_estimators, 'max_depth': max_depth}

    elif model_name == 'AB':
        n_estimators = int(n1 * 190 + 10)
        learning_rate = 0.1 + n2 * 1.9
        return {'n_estimators': n_estimators, 'learning_rate': learning_rate}

    return {}


def compute_boundary_grid(model, X_train, resolution=40):
    """Return (xx, yy, Z) meshgrid of normalised [0,1] predictions."""
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
    """Return per-model diagnostic dict for the /train endpoint."""
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
    elif model_name == 'GB':
        info['Num Estimators'] = model.n_estimators
        info['Max Depth'] = model.max_depth
        info['Learning Rate'] = model.learning_rate
    elif model_name == 'ET':
        info['Num Trees'] = len(model.estimators_)
        info['Max Depth'] = max(e.get_depth() for e in model.estimators_)
    elif model_name == 'AB':
        info['Num Estimators'] = model.n_estimators
        info['Learning Rate'] = model.learning_rate
    return info
