"""Vercel serverless function: /api/datasets

Returns the catalogue of available synthetic datasets with their
parameter ranges, complexity labels, and geometric descriptions.
Used by API consumers and the web UI to populate dataset selectors.

Args:
    req: Vercel serverless request object
    res: Vercel serverless response object with .json() method

Returns:
    JSON { datasets: [...], count: N }

Example:
    >>> curl https://your-app.vercel.app/api/datasets
    {"datasets": [{"name": "circles", ...}, ...], "count": 5}
"""

DATASET_CATALOGUE = [
    {
        'name': 'circles',
        'full_name': 'Concentric Circles',
        'description': (
            'Two concentric circles of points, one nested inside the other. '
            'A classic non-linearly separable dataset — trivial for RBF SVM '
            'and KNN, hard for linear models.'
        ),
        'complexity': 'low',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'SVM (RBF kernel) — easiest case',
            'Demonstrating kernel superiority over linear models',
            'Decision boundary visualisations',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points across both circles.',
            },
            'noise': {
                'type': 'float',
                'range': [0.0, 0.5],
                'default': 0.3,
                'description': 'Standard deviation of Gaussian noise added to points.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'noise': 0.3, 'seed': 42},
    },
    {
        'name': 'moons',
        'full_name': 'Crescent Moons',
        'description': (
            'Two interleaving half-circles (crescents). '
            'Similar to circles but with a single boundary arc, '
            'making it slightly harder to separate perfectly.'
        ),
        'complexity': 'low',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Non-linear classification demo',
            'Comparing SVM, KNN, and tree-based methods',
            'Interactive parameter exploration',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points across both moons.',
            },
            'noise': {
                'type': 'float',
                'range': [0.0, 0.5],
                'default': 0.3,
                'description': 'Standard deviation of Gaussian noise.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'noise': 0.3, 'seed': 42},
    },
    {
        'name': 'blobs',
        'full_name': 'Gaussian Blobs',
        'description': (
            'Two Gaussian clusters with configurable standard deviation (cluster_std=1.5). '
            'Well-separated and nearly linearly separable. '
            'Useful as a "too easy" baseline — most models achieve >95% accuracy.'
        ),
        'complexity': 'low',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Sanity-check baseline',
            'Linear model demos (LR, linear SVM)',
            'Quick feature engineering demos',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points across both blobs.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'seed': 42},
    },
    {
        'name': 'xor',
        'full_name': 'XOR Problem',
        'description': (
            'Four quadrants with diagonal class labels (top-left + bottom-right = class 1; '
            'top-right + bottom-left = class 0). '
            'Linearly inseparable — requires non-linear models to solve. '
            'A canonical test case for neural networks and RBF SVMs.'
        ),
        'complexity': 'medium',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Demonstrating linear model failure',
            'MLP and RBF SVM capability demos',
            'Logic gate analogy',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points (125 per quadrant).',
            },
            'noise': {
                'type': 'float',
                'range': [0.0, 1.0],
                'default': 0.3,
                'description': 'Standard deviation of noise added to each point.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'noise': 0.3, 'seed': 42},
    },
    {
        'name': 's_curve',
        'full_name': 'S-Curve (3D projection)',
        'description': (
            'A 3D S-shaped manifold projected to 2D, with y values binned into 2 classes. '
            'Creates a complex, non-planar decision boundary. '
            'Useful for demonstrating how tree ensembles and MLP handle '
            'manifold-structured data.'
        ),
        'complexity': 'high',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Tree-based model demos (RF, GB)',
            'MLP demos',
            'Showing how projection quality affects classification',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Number of points on the S-curve.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'seed': 42},
    },
    {
        'name': 'swiss_roll',
        'full_name': 'Swiss Roll Manifold',
        'description': (
            'A 3D swiss-roll manifold projected to 2D, with the manifold '
            'parameter binned into 2 classes. Creates a spiralling, non-planar '
            'boundary that challenges linear models and rewards tree/MLP approaches.'
        ),
        'complexity': 'high',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Tree-based model demos (RF, GB)',
            'MLP demos',
            'Manifold learning intuition',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Number of points on the swiss roll.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'seed': 42},
    },
    {
        'name': 'classification_2blobs',
        'full_name': 'Synthetic 2-Blobs (Linearly Separable)',
        'description': (
            'Two well-separated Gaussian clusters generated via '
            'make_classification (class_sep=2.0). '
            'Nearly linearly separable — a sanity-check baseline '
            'where most models achieve >95% accuracy.'
        ),
        'complexity': 'low',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Sanity-check baseline',
            'Linear model demos (LR, linear SVM)',
            'Quick feature engineering demos',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points across both blobs.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'seed': 42},
    },
    {
        'name': 'classification_concentric',
        'full_name': 'Dense Concentric Clusters',
        'description': (
            'Two dense, well-separated clusters (class_sep=5.0) generated via '
            'make_classification. More distinct than 2-blobs — a strong signal '
            'for even weak learners. Useful for demonstrating model robustness.'
        ),
        'complexity': 'low',
        'n_features': 2,
        'n_classes': 2,
        'recommended_for': [
            'Demonstrating model robustness to easy tasks',
            'KNN demos (very high accuracy expected)',
            'Baseline comparisons',
        ],
        'parameters': {
            'n_samples': {
                'type': 'int',
                'range': [100, 5000],
                'default': 500,
                'description': 'Total number of points across both clusters.',
            },
            'seed': {
                'type': 'int',
                'range': [0, 9999],
                'default': 42,
                'description': 'Random seed for reproducibility.',
            },
        },
        'defaults': {'n_samples': 500, 'seed': 42},
    },
]


def handle(req, res):
    """Vercel serverless handler — /api/datasets."""
    res.json({
        'datasets': DATASET_CATALOGUE,
        'count': len(DATASET_CATALOGUE),
    })
