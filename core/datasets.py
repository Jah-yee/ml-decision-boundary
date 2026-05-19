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


DATASET_GENERATORS = {
    'circles': lambda n, noise, seed: make_circles(n, noise, seed),
    'moons':    lambda n, noise, seed: make_moons(n, noise, seed),
    'blobs':    lambda n, noise, seed: make_blobs(n, noise, seed),
    'xor':      lambda n, noise, seed: make_xor(n, noise, seed),
    's_curve':  lambda n, noise, seed: make_s_curve(n, noise, seed),
}