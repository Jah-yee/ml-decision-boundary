"""
core/plugins/models/svm_plugin.py — Support Vector Machine plugin.

Demonstrates the ModelBuilder plugin interface.
Place in core/plugins/models/ to auto-register.
"""

from sklearn.svm import SVC

from core.interfaces import ModelBuilder


class SVMPlugin(ModelBuilder):
    """Support Vector Machine — implemented as a plugin."""

    name = "SVM"
    description = "Support Vector Machine (plugin-registered)"

    def build(self, **kwargs):
        # Always add random_state for reproducibility
        return SVC(**kwargs, random_state=42)

    def default_params(self):
        return {"kernel": "rbf", "C": 1.0, "gamma": "scale"}

    def hyperparameter_space(self):
        return {
            "C": [0.1, 1.0, 10.0],
            "kernel": ["linear", "rbf", "poly"],
            "gamma": ["scale", "auto", 0.01, 0.1],
        }