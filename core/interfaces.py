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