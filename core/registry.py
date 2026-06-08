"""
core/registry.py — Model Registry & Lifecycle Management

v8 DoD #1: Auto-registers training results to ~/.ml-decision-boundary/registry/
v8 DoD #2: save_model() / load_model() interfaces

Registry structure:
  ~/.ml-decision-boundary/registry/
  ├── models/
  │   ├── 2026-06-07_abc123.json   # metadata
  │   ├── 2026-06-07_abc123.joblib # serialized model
  │   └── ...
  └── benchmarks/
      ├── 2026-06-07_xyz789.json
      └── ...
"""

import json
import hashlib
import joblib
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict


REGISTRY_BASE = Path.home() / ".ml-decision-boundary" / "registry"
MODELS_DIR = REGISTRY_BASE / "models"
BENCHMARKS_DIR = REGISTRY_BASE / "benchmarks"


@dataclass
class ModelMetadata:
    """Schema for a registered model."""
    id: str                    # 2026-06-07_abc123
    model_type: str            # SVM, Tree, RF, ...
    hyperparameters: Dict[str, Any]
    dataset: Dict[str, Any]    # name, n_samples, hash
    metrics: Dict[str, Any]    # train_accuracy, test_accuracy
    created_at: str             # ISO8601 with timezone
    plugin_origin: bool        # True if loaded from plugin
    joblib_path: str           # relative path to .joblib file
    accuracy: float            # primary metric (test accuracy)
    plugin_state: Optional[Dict[str, Any]] = None  # v8 DoD #2: plugin serialization state


class RegistryManager:
    """
    Manages model registration, persistence, and lifecycle.

    Usage:
        rm = RegistryManager()
        model_id = rm.save_model(model, model_type="SVM", ...)
        loaded = rm.load_model(model_id)
        all_models = rm.list_models()
        rm.delete_model(model_id)
    """

    def __init__(self, registry_base: Path = REGISTRY_BASE):
        self.registry_base = Path(registry_base)
        self.models_dir = self.registry_base / "models"
        self.benchmarks_dir = self.registry_base / "benchmarks"
        self._ensure_dirs()

    def _ensure_dirs(self):
        """Create registry directories if they don't exist."""
        self.models_dir.mkdir(parents=True, exist_ok=True)
        self.benchmarks_dir.mkdir(parents=True, exist_ok=True)

    # ── Hashing ────────────────────────────────────────────────────────────────

    @staticmethod
    def _dataset_hash(X, y) -> str:
        """Compute sha256 hash of dataset for fingerprinting."""
        data = f"{X.shape[0]}_{X.tobytes().hex()[:32]}_{y.tobytes().hex()[:32]}"
        return "sha256:" + hashlib.sha256(data.encode()).hexdigest()[:16]

    @staticmethod
    def _short_id() -> str:
        """Generate a short unique suffix from timestamp + random."""
        import random
        suffix = hashlib.sha256(
            f"{time.time():.6f}{random.random()}".encode()
        ).hexdigest()[:6]
        return suffix

    # ── Save / Load ────────────────────────────────────────────────────────────

    def save_model(
        self,
        model: Any,
        model_type: str,
        hyperparameters: Dict[str, Any],
        X_train=None,
        y_train=None,
        X_test=None,
        y_test=None,
        dataset_name: str = "unknown",
        n_samples: int = 0,
        train_accuracy: float = 0.0,
        test_accuracy: float = 0.0,
        plugin_origin: bool = False,
        plugin_state: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Persist a trained model to the registry.

        Returns:
            model_id: str, the unique ID for this model (e.g. "2026-06-07_abc123")
        """
        self._ensure_dirs()

        # Generate unique ID
        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_id = self._short_id()
        model_id = f"{date_str}_{short_id}"

        # Dataset hash
        dataset_hash = "unknown"
        if X_train is not None and y_train is not None:
            dataset_hash = self._dataset_hash(X_train, y_train)

        # Paths
        json_path = self.models_dir / f"{model_id}.json"
        joblib_path = self.models_dir / f"{model_id}.joblib"

        # Serialize model
        joblib.dump(model, joblib_path)

        # Build metadata
        metadata = ModelMetadata(
            id=model_id,
            model_type=model_type,
            hyperparameters=hyperparameters,
            dataset={
                "name": dataset_name,
                "n_samples": n_samples,
                "hash": dataset_hash,
            },
            metrics={
                "train_accuracy": round(train_accuracy, 4),
                "test_accuracy": round(test_accuracy, 4),
            },
            created_at=datetime.now(timezone.utc).isoformat(),
            plugin_origin=plugin_origin,
            joblib_path=str(joblib_path.relative_to(self.registry_base)),
            accuracy=round(test_accuracy, 4),
            plugin_state=plugin_state,
        )

        # Write metadata JSON
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

        return model_id

    def load_model(self, model_id: str) -> Any:
        """
        Load a registered model from the registry by ID.

        Args:
            model_id: e.g. "2026-06-07_abc123"

        Returns:
            The deserialized sklearn estimator.

        Raises:
            FileNotFoundError: if model_id not found.
        """
        json_path = self.models_dir / f"{model_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Model '{model_id}' not found in registry. "
                f"Run 'ml-db model list' to see available models."
            )

        with open(json_path, encoding="utf-8") as f:
            metadata = json.load(f)

        joblib_path = self.registry_base / metadata["joblib_path"]
        if not joblib_path.exists():
            raise FileNotFoundError(
                f"Model file for '{model_id}' not found at {joblib_path}. "
                f"Registry may be corrupted."
            )

        # v8 DoD #2: handle plugin models via from_state()
        plugin_state = metadata.get("plugin_state")
        if metadata.get("plugin_origin") and plugin_state:
            plugin_name = plugin_state.get("plugin_name", metadata.get("model_type", ""))
            # Dynamically import plugin registry to avoid circular imports
            from core.plugins.registry import get_plugin_model
            plugin = get_plugin_model(plugin_name)
            if plugin is not None and hasattr(plugin, "from_state"):
                builder = plugin.from_state(plugin_state)
                # Build model with restored hyperparameters
                model = builder.build(**plugin_state.get("hyperparameters", {}))
                return model

        return joblib.load(joblib_path)

    def get_metadata(self, model_id: str) -> Dict[str, Any]:
        """Return metadata dict for a model without loading the model object."""
        json_path = self.models_dir / f"{model_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered models, newest first.
        """
        models = []
        for json_file in sorted(self.models_dir.glob("*.json"), reverse=True):
            try:
                with open(json_file, encoding="utf-8") as f:
                    models.append(json.load(f))
            except Exception:
                # Skip corrupted metadata files
                continue
        return models

    def delete_model(self, model_id: str) -> None:
        """
        Delete a model and its files from the registry.

        Raises:
            FileNotFoundError: if model_id not found.
        """
        json_path = self.models_dir / f"{model_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )

        with open(json_path, encoding="utf-8") as f:
            metadata = json.load(f)

        joblib_path = self.registry_base / metadata["joblib_path"]
        if joblib_path.exists():
            joblib_path.unlink()

        json_path.unlink()

    # ── CLI helpers ────────────────────────────────────────────────────────────

    def find_model(self, model_id: str) -> bool:
        """Return True if model_id exists in registry."""
        return (self.models_dir / f"{model_id}.json").exists()


# ── Module-level singleton (lazy) ─────────────────────────────────────────────

_default_manager: Optional[RegistryManager] = None


def get_registry_manager() -> RegistryManager:
    """Get or create the default RegistryManager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = RegistryManager()
    return _default_manager
