"""
core/plugins/registry.py — Plugin discovery and registration.

Automatically discovers model plugins from core/plugins/models/ directory.
Plugins are Python files (not __init__.py, not starting with _) that
implement the ModelBuilder interface.
"""

import os
import importlib
import sys
from pathlib import Path
from typing import Dict, List, Type

# Ensure project root is in path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from core.interfaces import ModelBuilder


def discover_plugins() -> Dict[str, Type[ModelBuilder]]:
    """
    Scan core/plugins/models/ for ModelBuilder implementations.

    Returns:
        Dict mapping model name (lowercase) → plugin class.

    Raises:
        PluginError: if a plugin file cannot be imported or is malformed.
    """
    plugins_dir = Path(__file__).parent / "models"
    if not plugins_dir.exists():
        return {}

    discovered = {}
    for filename in os.listdir(plugins_dir):
        if filename.startswith("_") or filename == "__init__.py":
            continue
        if not filename.endswith(".py"):
            continue

        module_name = filename[:-3]  # strip .py
        try:
            # Import from core.plugins.models.<module_name>
            full_module = f"core.plugins.models.{module_name}"
            module = importlib.import_module(full_module)

            # Find ModelBuilder subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, ModelBuilder)
                    and attr is not ModelBuilder
                ):
                    # Register by plugin.name (lowercase for consistency)
                    plugin_instance = attr()
                    key = plugin_instance.name.lower()  # lowercase for case-insensitive lookup
                    discovered[key] = attr

        except Exception as e:
            raise PluginError(f"Failed to load plugin '{module_name}': {e}")

    return discovered


class PluginError(Exception):
    """Raised when plugin loading fails."""
    pass


def get_plugin_model(name: str) -> ModelBuilder:
    """
    Get a plugin instance by name. Returns None if not found.

    Args:
        name: plugin name (case-insensitive)

    Returns:
        ModelBuilder instance or None.
    """
    plugins = discover_plugins()
    cls = plugins.get(name.lower())  # keys are lowercase
    if cls is not None:
        return cls()  # return instance, not class
    return None


# ─────────────────────────────────────────────────────────────────────────────
# Builtin model factory adapters (makes builtin models pluggable too)
# ─────────────────────────────────────────────────────────────────────────────

def _make_svm_plugin():
    """SVM as a plugin (verifies interface compatibility)."""
    from sklearn.svm import SVC

    class SVMPlugin(ModelBuilder):
        name = "SVM"
        description = "Support Vector Machine (sklearn SVC)"

        def build(self, **kwargs):
            return SVC(**kwargs, random_state=42)

        def default_params(self):
            return {"kernel": "rbf", "C": 1.0, "gamma": "scale"}

        def hyperparameter_space(self):
            return {
                "C": [0.1, 1.0, 10.0],
                "kernel": ["linear", "rbf", "poly"],
                "gamma": ["scale", "auto", 0.01, 0.1],
            }

    return SVMPlugin()


# Pre-load builtins so we always have fallback
BUILTIN_PLUGINS = {
    "svm": _make_svm_plugin(),  # key must be lowercase
}