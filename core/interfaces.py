"""
core/interfaces.py — Abstract interfaces for plugin system.

Defines the contract that all plugins must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List


class ModelBuilder(ABC):
    """
    Abstract interface for model builder plugins.

    Implement this class to add custom models to ml-decision-boundary.
    Place your plugin in core/plugins/models/ directory.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """CLI name for this model (e.g., 'SVM', 'RF')."""
        pass

    @property
    def description(self) -> str:
        """Human-readable description for --list-models."""
        return f"{self.name} (plugin)"

    @abstractmethod
    def build(self, **kwargs) -> Any:
        """Build and return an sklearn estimator instance."""
        pass

    def default_params(self) -> Dict[str, Any]:
        """Default hyperparameter values."""
        return {}

    def hyperparameter_space(self) -> Dict[str, List[Any]]:
        """
        Return a dict of parameter → list of candidate values.
        Used by slider_to_params when generating param combinations.
        """
        return {}

    # ── Serialization protocol (v8 DoD #2) ──────────────────────────────────

    def get_state(self) -> Dict[str, Any]:
        """
        Serialize plugin model state for registry persistence.

        Returns a dict with at minimum:
          - plugin_name: str (the plugin's registered name)
          - hyperparameters: dict (current hyperparameter values)

        Subclasses may include additional serializable fields.
        Built-in sklearn models (SVM, Tree, etc.) use joblib directly
        and do not need to implement this method.
        """
        return {"plugin_name": self.name, "hyperparameters": self.default_params()}

    @classmethod
    def from_state(cls, state: Dict[str, Any]) -> "ModelBuilder":
        """
        Reconstruct a ModelBuilder instance from serialized state.

        Args:
            state: dict as produced by get_state()

        Returns:
            A new ModelBuilder instance with hyperparameters restored.
        """
        instance = cls()
        return instance