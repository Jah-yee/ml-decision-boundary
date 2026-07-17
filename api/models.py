"""Vercel serverless function: /api/models/<name>

Returns model metadata: parameter ranges, default values, applicable
scenarios, and complexity level. Used by API consumers and the web UI
to build dynamic parameter controls.

Args:
    req: Vercel serverless request object
    res: Vercel serverless response object with .json() method

Query / path:
    The model name is extracted from the URL path segment after /api/models/

Returns:
    JSON { name, description, complexity, parameter_ranges, defaults, scenarios }

Example:
    >>> curl https://your-app.vercel.app/api/models/SVM
    {"name": "SVM", "description": "Support Vector Machine ...", ...}
"""

# ─── Model metadata catalogue ─────────────────────────────────────────────

MODEL_CATALOGUE = {
    'SVM': {
        'name': 'SVM',
        'full_name': 'Support Vector Machine',
        'description': (
            'Finds the maximum-margin hyperplane that separates classes. '
            'Excellent for high-dimensional data and non-linear boundaries '
            'via the RBF kernel. Sensitive to feature scaling.'
        ),
        'complexity': 'medium',
        'parameters': {
            'C': {
                'type': 'float',
                'range': [0.1, 100.0],
                'default': 1.0,
                'slider_range': [0, 100],   # maps to p1 0-100 → C
                'description': 'Regularisation strength. Larger = harder margin.',
            },
            'gamma': {
                'type': 'select',
                'options': ['scale', 'auto', 0.01, 0.1, 1.0, 10.0],
                'default': 'scale',
                'slider_range': [0, 100],   # maps to p2 0-100 → gamma index
                'description': 'RBF kernel coefficient. "scale" = 1/(n_features*X.var()).',
            },
            'kernel': {
                'type': 'constant',
                'value': 'rbf',
                'description': 'Kernel type used for decision boundary.',
            },
        },
        'defaults': {'kernel': 'rbf', 'C': 1.0, 'gamma': 'scale'},
        'scenarios': [
            'High-dimensional classification',
            'Non-linear decision boundaries',
            'Text / image classification (after embedding)',
        ],
        'presets': {
            'balanced':  {'C': 1.0,  'gamma': 'scale'},
            'high_accuracy': {'C': 10.0, 'gamma': 0.1},
            'lightweight':   {'C': 0.1,  'gamma': 'scale'},
        },
    },
    'LR': {
        'name': 'LR',
        'full_name': 'Logistic Regression',
        'description': (
            'Linear model that estimates class probabilities using the logistic function. '
            'Interpretable, fast, and works well as a baseline. '
            'L2 regularisation controlled by C.'
        ),
        'complexity': 'low',
        'parameters': {
            'C': {
                'type': 'float',
                'range': [0.1, 100.0],
                'default': 1.0,
                'slider_range': [0, 100],
                'description': 'Inverse regularisation strength. Larger = less regularisation.',
            },
            'max_iter': {
                'type': 'constant',
                'value': 1000,
                'description': 'Maximum iterations for solver convergence.',
            },
        },
        'defaults': {'C': 1.0, 'max_iter': 1000},
        'scenarios': [
            'Baseline binary / multi-class classification',
            'When interpretability is critical',
            'Probabilistic output needed',
        ],
        'presets': {
            'balanced':        {'C': 1.0},
            'high_accuracy':   {'C': 10.0},
            'lightweight':     {'C': 0.1},
        },
    },
    'Tree': {
        'name': 'Tree',
        'full_name': 'Decision Tree',
        'description': (
            'Axiomatically splits data along feature axes to maximise information gain. '
            'Highly interpretable, fast, and prone to overfitting when deep.'
        ),
        'complexity': 'low',
        'parameters': {
            'max_depth': {
                'type': 'int',
                'range': [1, 20],
                'default': 5,
                'slider_range': [0, 100],
                'description': 'Maximum tree depth. Deeper = more complex boundary.',
            },
            'min_samples_split': {
                'type': 'int',
                'range': [2, 22],
                'default': 2,
                'slider_range': [0, 100],
                'description': 'Min samples required to split an internal node.',
            },
        },
        'defaults': {'max_depth': 5, 'min_samples_split': 2},
        'scenarios': [
            'Interpretability required',
            'Feature importance analysis',
            'Fast prototyping',
        ],
        'presets': {
            'balanced':      {'max_depth': 5,  'min_samples_split': 2},
            'high_accuracy': {'max_depth': 15, 'min_samples_split': 2},
            'lightweight':   {'max_depth': 3,  'min_samples_split': 10},
        },
    },
    'RF': {
        'name': 'RF',
        'full_name': 'Random Forest',
        'description': (
            'Ensemble of decision trees, each trained on a bootstrapped subset of data. '
            'Reduces overfitting compared to a single tree while retaining interpretability '
            '(via feature importance).'
        ),
        'complexity': 'medium',
        'parameters': {
            'n_estimators': {
                'type': 'int',
                'range': [10, 200],
                'default': 100,
                'slider_range': [0, 100],
                'description': 'Number of trees in the forest.',
            },
            'max_depth': {
                'type': 'int',
                'range': [1, 20],
                'default': 10,
                'slider_range': [0, 100],
                'description': 'Maximum depth of each tree.',
            },
        },
        'defaults': {'n_estimators': 100, 'max_depth': 10},
        'scenarios': [
            'General-purpose classification with good accuracy',
            'Feature importance ranking',
            'Noisy data with many features',
        ],
        'presets': {
            'balanced':      {'n_estimators': 100, 'max_depth': 10},
            'high_accuracy': {'n_estimators': 200, 'max_depth': 20},
            'lightweight':   {'n_estimators': 10,  'max_depth': 5},
        },
    },
    'KNN': {
        'name': 'KNN',
        'full_name': 'K-Nearest Neighbours',
        'description': (
            'Instance-based learner: classifies a point by majority vote of its '
            'k nearest neighbours. No explicit training phase (lazy). '
            'Sensitive to the choice of k and to noisy / high-dimensional data.'
        ),
        'complexity': 'low',
        'parameters': {
            'n_neighbors': {
                'type': 'int',
                'range': [1, 50],
                'default': 5,
                'slider_range': [0, 100],
                'description': 'Number of neighbours to consider.',
            },
        },
        'defaults': {'n_neighbors': 5},
        'scenarios': [
            'Small to medium datasets',
            'Non-linear boundaries',
            'As a baseline before more complex models',
        ],
        'presets': {
            'balanced':      {'n_neighbors': 5},
            'high_accuracy': {'n_neighbors': 3},
            'lightweight':   {'n_neighbors': 15},
        },
    },
    'MLP': {
        'name': 'MLP',
        'full_name': 'Multi-Layer Perceptron',
        'description': (
            'Feed-forward neural network with one hidden layer. '
            'Can learn very complex non-linear decision boundaries. '
            'Sensitive to hyperparameters and feature scaling.'
        ),
        'complexity': 'high',
        'parameters': {
            'hidden_layer_sizes': {
                'type': 'int',
                'range': [10, 200],
                'default': 100,
                'slider_range': [0, 100],
                'description': 'Number of neurons in the single hidden layer.',
            },
            'alpha': {
                'type': 'float',
                'range': [0.0, 0.1],
                'default': 0.0001,
                'slider_range': [0, 100],
                'description': 'L2 regularisation penalty.',
            },
            'max_iter': {
                'type': 'constant',
                'value': 500,
                'description': 'Maximum optimisation iterations.',
            },
        },
        'defaults': {'hidden_layer_sizes': (100,), 'alpha': 0.0001, 'max_iter': 500},
        'scenarios': [
            'Complex non-linear boundaries',
            'When other models plateau',
            'Deep feature learning (multi-layer, future work)',
        ],
        'presets': {
            'balanced':      {'hidden_layer_sizes': (100,), 'alpha': 0.001},
            'high_accuracy': {'hidden_layer_sizes': (200,), 'alpha': 0.0001},
            'lightweight':   {'hidden_layer_sizes': (20,),  'alpha': 0.01},
        },
    },
    'GB': {
        'name': 'GB',
        'full_name': 'Gradient Boosting',
        'description': (
            'Sequential ensemble that builds trees to correct residual errors. '
            'State-of-the-art for tabular data. Slower but often more accurate than RF.'
        ),
        'complexity': 'high',
        'parameters': {
            'n_estimators': {
                'type': 'int',
                'range': [10, 200],
                'default': 100,
                'slider_range': [0, 100],
                'description': 'Number of boosting stages.',
            },
            'max_depth': {
                'type': 'int',
                'range': [1, 20],
                'default': 3,
                'slider_range': [0, 100],
                'description': 'Maximum depth of each tree.',
            },
            'learning_rate': {
                'type': 'float',
                'range': [0.05, 0.2],
                'default': 0.1,
                'slider_range': [0, 100],
                'description': 'Shrinkage rate applied to each stage.',
            },
        },
        'defaults': {'n_estimators': 100, 'max_depth': 3, 'learning_rate': 0.1},
        'scenarios': [
            'Kaggle-style tabular competition baseline',
            'High accuracy requirements',
            'Noisy data with complex interactions',
        ],
        'presets': {
            'balanced':      {'n_estimators': 100, 'max_depth': 3,  'learning_rate': 0.1},
            'high_accuracy': {'n_estimators': 200, 'max_depth': 5,  'learning_rate': 0.05},
            'lightweight':   {'n_estimators': 20,  'max_depth': 2,  'learning_rate': 0.2},
        },
    },
    'ET': {
        'name': 'ET',
        'full_name': 'Extra Trees',
        'description': (
            'Extremely randomised trees: like RF but each tree is trained on '
            'the full dataset and splits are chosen completely at random. '
            'Faster than RF, sometimes better, often more variance.'
        ),
        'complexity': 'medium',
        'parameters': {
            'n_estimators': {
                'type': 'int',
                'range': [10, 200],
                'default': 100,
                'slider_range': [0, 100],
                'description': 'Number of trees.',
            },
            'max_depth': {
                'type': 'int',
                'range': [1, 20],
                'default': 10,
                'slider_range': [0, 100],
                'description': 'Maximum depth of each tree.',
            },
        },
        'defaults': {'n_estimators': 100, 'max_depth': 10},
        'scenarios': [
            'Faster alternative to RF',
            'High-dimensional data',
            'When training time is constrained',
        ],
        'presets': {
            'balanced':      {'n_estimators': 100, 'max_depth': 10},
            'high_accuracy': {'n_estimators': 200, 'max_depth': 20},
            'lightweight':   {'n_estimators': 10,  'max_depth': 5},
        },
    },
    'AB': {
        'name': 'AB',
        'full_name': 'AdaBoost',
        'description': (
            'Adaptive boosting: trains weak learners sequentially, '
            'reweighting samples to focus on misclassified points. '
            'Simple and effective for low-dimensional data.'
        ),
        'complexity': 'medium',
        'parameters': {
            'n_estimators': {
                'type': 'int',
                'range': [10, 200],
                'default': 50,
                'slider_range': [0, 100],
                'description': 'Maximum number of weak learners.',
            },
            'learning_rate': {
                'type': 'float',
                'range': [0.1, 2.0],
                'default': 1.0,
                'slider_range': [0, 100],
                'description': 'Weight applied to each weak learner.',
            },
        },
        'defaults': {'n_estimators': 50, 'learning_rate': 1.0},
        'scenarios': [
            'Low-dimensional data',
            'Combining many weak learners',
            'Speed-sensitive applications',
        ],
        'presets': {
            'balanced':      {'n_estimators': 50,  'learning_rate': 1.0},
            'high_accuracy':  {'n_estimators': 200, 'learning_rate': 0.5},
            'lightweight':    {'n_estimators': 10,  'learning_rate': 2.0},
        },
    },
    'NB': {
        'name': 'NB',
        'full_name': 'Gaussian Naive Bayes',
        'description': (
            'Probabilistic classifier assuming feature independence given the class. '
            'Extremely fast and simple, a strong baseline for text and multi-class '
            'problems despite the independence assumption.'
        ),
        'complexity': 'low',
        'parameters': {},
        'defaults': {},
        'scenarios': [
            'Fast baseline for any classification task',
            'Text classification (with bag-of-words)',
            'Multi-class with many features',
        ],
        'presets': {
            'balanced': {},
            'high_accuracy': {},
            'lightweight': {},
        },
    },
}


def handle(req, res):
    """Vercel serverless handler — routes /api/models/*."""
    import json as _json

    path = req.url.split('?')[0].rstrip('/')
    # Expected path: /api/models/<name>
    prefix = '/api/models'
    if not path.startswith(prefix):
        res.status = 404
        res.json({'error': f'Unhandled path: {path}'})
        return

    name = path[len(prefix):].lstrip('/')

    if not name:
        # Return catalogue overview
        res.json({
            'models': list(MODEL_CATALOGUE.keys()),
            'count': len(MODEL_CATALOGUE),
        })
        return

    if name not in MODEL_CATALOGUE:
        res.status = 404
        res.json({
            'error': f"Unknown model: '{name}'",
            'available': list(MODEL_CATALOGUE.keys()),
        })
        return

    res.json(MODEL_CATALOGUE[name])
