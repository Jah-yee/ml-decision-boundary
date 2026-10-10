"""
core/datasets.py — Shared dataset generators

All dataset factory functions live here once.  api/train.py, web/server.py,
and main.py import from here instead of maintaining copies.
"""

import numpy as np


def make_circles(n, noise, seed):
    from sklearn.datasets import make_circles as sk_circles
    X, y = sk_circles(n_samples=n, noise=noise, random_state=seed, factor=0.5)
    return X, y


def make_moons(n, noise, seed):
    from sklearn.datasets import make_moons as sk_moons
    X, y = sk_moons(n_samples=n, noise=noise, random_state=seed)
    return X, y


def make_blobs(n, _noise, seed):
    from sklearn.datasets import make_blobs
    X, y = make_blobs(n_samples=n, centers=2, random_state=seed, cluster_std=1.5)
    return X, y


def make_xor(n, noise, seed):
    np.random.seed(seed)
    X = np.random.randn(n, 2)
    y = ((X[:, 0] > 0) ^ (X[:, 1] > 0)).astype(int)
    X += np.random.randn(n, 2) * noise
    return X, y


def make_s_curve(n, _noise, seed):
    from sklearn.datasets import make_s_curve as sk_s_curve
    from sklearn.preprocessing import KBinsDiscretizer

    X, y = sk_s_curve(n_samples=n, noise=0.0, random_state=seed)
    # Project 3D S-curve to 2D and bin y into 2 classes
    kbd = KBinsDiscretizer(n_bins=2, encode='ordinal', strategy='quantile')
    y_bin = kbd.fit_transform(y.reshape(-1, 1)).ravel().astype(int)
    return X[:, :2], y_bin


def make_swiss_roll(n, _noise, seed):
    """Swiss roll manifold projected to 2D with 2-class binning."""
    from sklearn.datasets import make_swiss_roll as sk_swiss_roll
    from sklearn.preprocessing import KBinsDiscretizer

    X, t = sk_swiss_roll(n_samples=n, noise=0.0, random_state=seed)
    # Bin the manifold parameter t into 2 classes for classification
    kbd = KBinsDiscretizer(n_bins=2, encode='ordinal', strategy='quantile')
    y_bin = kbd.fit_transform(t.reshape(-1, 1)).ravel().astype(int)
    return X[:, :2], y_bin


def make_classification_2blobs(n, _noise, seed):
    """Linearly separable 2-blobs — class_sep=2.0 makes it easy for all models."""
    from sklearn.datasets import make_classification
    X, y = make_classification(
        n_samples=n,
        n_features=2,
        n_informative=2,
        n_redundant=0,
        n_classes=2,
        n_clusters_per_class=1,
        class_sep=2.0,
        random_state=seed,
    )
    return X, y


def make_classification_concentric(n, _noise, seed):
    """Dense concentric clusters — class_sep=5.0 makes very distinct classes."""
    from sklearn.datasets import make_classification
    X, y = make_classification(
        n_samples=n,
        n_features=2,
        n_informative=2,
        n_redundant=0,
        n_classes=2,
        n_clusters_per_class=1,
        class_sep=5.0,
        random_state=seed,
    )
    return X, y


DATASET_GENERATORS = {
    'circles':                   lambda n, noise, seed: make_circles(n, noise, seed),
    'moons':                      lambda n, noise, seed: make_moons(n, noise, seed),
    'blobs':                      lambda n, noise, seed: make_blobs(n, noise, seed),
    'xor':                        lambda n, noise, seed: make_xor(n, noise, seed),
    's_curve':                    lambda n, noise, seed: make_s_curve(n, noise, seed),
    'swiss_roll':                 lambda n, noise, seed: make_swiss_roll(n, noise, seed),
    'classification_2blobs':      lambda n, noise, seed: make_classification_2blobs(n, noise, seed),
    'classification_concentric':  lambda n, noise, seed: make_classification_concentric(n, noise, seed),
}