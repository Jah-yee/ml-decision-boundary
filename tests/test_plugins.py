"""
tests/test_plugins.py — Plugin system tests (v7 DoD #1)

Tests the custom model plugin interface in core/plugins/.
Covers: plugin discovery, ModelBuilder interface, build_model integration.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.interfaces import ModelBuilder
from core.plugins.registry import discover_plugins, get_plugin_model, PluginError, BUILTIN_PLUGINS
from core.train_utils import build_model


class TestModelBuilderInterface:
    """Test that ModelBuilder abstract interface is correctly defined."""

    def test_model_builder_is_abstract(self):
        """ModelBuilder cannot be instantiated directly."""
        with pytest.raises(TypeError):
            ModelBuilder()

    def test_model_builder_has_required_properties(self):
        """ModelBuilder defines name property and build method."""
        assert hasattr(ModelBuilder, 'name')
        assert hasattr(ModelBuilder, 'build')


class TestPluginDiscovery:
    """Test plugin discovery from core/plugins/models/."""

    def test_discover_plugins_returns_dict(self):
        """discover_plugins() returns a dict of plugin_name -> class."""
        plugins = discover_plugins()
        assert isinstance(plugins, dict)

    def test_svm_plugin_discovered(self):
        """SVM plugin is discovered from core/plugins/models/."""
        plugins = discover_plugins()
        assert 'svm' in plugins, f"Expected 'svm' in plugins, got: {list(plugins.keys())}"

    def test_svm_plugin_is_model_builder_subclass(self):
        """Discovered SVM plugin is a ModelBuilder subclass."""
        plugins = discover_plugins()
        svm_cls = plugins['svm']
        assert issubclass(svm_cls, ModelBuilder)
        assert svm_cls is not ModelBuilder


class TestPluginModelBuilder:
    """Test that plugin-based models can be built."""

    def test_get_plugin_model_svm(self):
        """get_plugin_model('SVM') returns SVMPlugin."""
        plugin = get_plugin_model('SVM')
        assert plugin is not None

    def test_get_plugin_model_case_insensitive(self):
        """get_plugin_model is case-insensitive."""
        plugin_lower = get_plugin_model('svm')
        plugin_upper = get_plugin_model('SVM')
        assert plugin_lower is not None
        assert plugin_upper is not None

    def test_svm_plugin_build(self):
        """SVMPlugin.build() returns an SVC instance."""
        plugin = get_plugin_model('SVM')
        model = plugin.build(kernel='rbf', C=1.0)
        assert model is not None
        # Should be a callable sklearn estimator
        assert hasattr(model, 'fit')
        assert hasattr(model, 'predict')

    def test_svm_plugin_default_params(self):
        """SVMPlugin.default_params() returns dict."""
        plugin = get_plugin_model('SVM')
        defaults = plugin.default_params()
        assert isinstance(defaults, dict)
        assert 'kernel' in defaults
        assert 'C' in defaults

    def test_svm_plugin_hyperparameter_space(self):
        """SVMPlugin.hyperparameter_space() returns dict of lists."""
        plugin = get_plugin_model('SVM')
        space = plugin.hyperparameter_space()
        assert isinstance(space, dict)
        assert 'C' in space
        assert isinstance(space['C'], list)


class TestBuildModelPluginIntegration:
    """Test that build_model uses plugin system correctly."""

    def test_build_model_svm_via_plugin(self):
        """build_model('SVM', {}) returns a model."""
        model = build_model('SVM', {'kernel': 'rbf', 'C': 1.0})
        assert model is not None
        assert hasattr(model, 'fit')
        assert hasattr(model, 'predict')

    def test_build_model_builtin_still_works(self):
        """build_model with builtin model (RF) still works."""
        model = build_model('RF', {'n_estimators': 10, 'max_depth': 5})
        assert model is not None
        assert hasattr(model, 'fit')

    def test_build_model_unknown_gives_helpful_error(self):
        """build_model with unknown model gives error with available options."""
        with pytest.raises(ValueError) as exc_info:
            build_model('unknown-model-xyz', {})
        error_msg = str(exc_info.value)
        # Should mention it's unknown and list available models
        assert 'unknown-model-xyz' in error_msg
        assert 'Available models:' in error_msg or 'SVM' in error_msg


class TestBuiltinPlugins:
    """Test that BUILTIN_PLUGINS dict is populated."""
    def test_builtin_plugins_not_empty(self):
        """BUILTIN_PLUGINS has at least one entry."""
        assert len(BUILTIN_PLUGINS) >= 1

    def test_builtin_svm_in_builtins(self):
        """SVM is available in BUILTIN_PLUGINS."""
        assert 'svm' in BUILTIN_PLUGINS