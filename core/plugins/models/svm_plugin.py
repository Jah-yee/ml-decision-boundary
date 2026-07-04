"""
core/plugins/models/svm_plugin.py — Support Vector Machine plugin.

Demonstrates the ModelBuilder plugin interface.
Place in core/plugins/models/ to auto-register.
"""

from typing import Dict, Any

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

    def get_state(self) -> Dict[str, Any]:
        """Serialize SVM plugin state for registry persistence."""
        return {
            "plugin_name": self.name,
            "hyperparameters": self.default_params(),
        }

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "SVMPlugin":
        """Reconstruct SVMPlugin from serialized state."""
        instance = cls()
        return instance