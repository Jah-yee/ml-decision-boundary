"""
core/registry.py — Model Registry & Lifecycle Management

v8 DoD #1: Auto-registers training results to ~/.ml-decision-boundary/registry/
v8 DoD #2: save_model() / load_model() interfaces
v9 DoD #3: compare / tag / untag / list_tags / list_models_by_tag

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
from dataclasses import dataclass, asdict, field


REGISTRY_BASE = Path.home() / ".ml-decision-boundary" / "registry"
REGRESSION_THRESHOLD = 0.05  # 5% accuracy drop triggers regression flag
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
    tags: List[str] = field(default_factory=list)  # v9 DoD #3: user-assigned labels


@dataclass
class BenchmarkMetadata:
    """Schema for a registered benchmark run. v8 DoD #4."""
    id: str                         # 2026-06-07_xyz789
    mode: str                       # "full" | "quick" | "depth_sweep" | "hyperparam_sweep"
    timestamp: str                   # ISO8601 with timezone
    duration_seconds: float
    git_hash: str                   # git commit hash, "unknown" if unavailable
    total_experiments: int
    passed: int
    failed: int
    regressions: int
    model_results: list = field(default_factory=list)   # per-experiment records
    regression_details: list = field(default_factory=list)  # {dataset, model, acc, baseline_acc}
    report_json: str = ""
    report_md: str = ""


class RegistryManager:
    """
    Manages model registration, persistence, and lifecycle.

    Usage:
        rm = RegistryManager()
        model_id = rm.save_model(model, model_type="SVM", ...)
        loaded = rm.load_model(model_id)
        all_models = rm.list_models()
        rm.delete_model(model_id)
        rm.tag_model(model_id, "best-for-circles")
        rm.compare_models(id1, id2)
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
            tags=[],  # v9 DoD #3: initialized empty
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

    def _write_metadata(self, model_id: str, metadata: Dict[str, Any]) -> None:
        """Write metadata dict back to the JSON file. Internal use only."""
        json_path = self.models_dir / f"{model_id}.json"
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(metadata, f, indent=2, ensure_ascii=False)

    def list_models(self) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered models, newest first (by created_at).
        """
        models = []
        for json_file in self.models_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    models.append(json.load(f))
            except Exception:
                # Skip corrupted metadata files
                continue
        # Sort by created_at descending (newest first)
        models.sort(key=lambda m: m.get("created_at", ""), reverse=True)
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

    # ── v9 DoD #3: Tags & Compare ──────────────────────────────────────────────

    def tag_model(self, model_id: str, tag: str) -> None:
        """
        Add a tag to a model.  v9 DoD #3.

        Raises:
            FileNotFoundError: if model_id not found.
            ValueError: if tag is already present.
        """
        if not self.find_model(model_id):
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        meta = self.get_metadata(model_id)
        tags: List[str] = meta.get("tags", [])
        if tag in tags:
            raise ValueError(f"Tag '{tag}' already exists on model '{model_id}'.")
        tags.append(tag)
        meta["tags"] = tags
        self._write_metadata(model_id, meta)

    def untag_model(self, model_id: str, tag: str) -> None:
        """
        Remove a tag from a model.  v9 DoD #3.

        Raises:
            FileNotFoundError: if model_id not found.
            ValueError: if tag is not present.
        """
        if not self.find_model(model_id):
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        meta = self.get_metadata(model_id)
        tags: List[str] = meta.get("tags", [])
        if tag not in tags:
            raise ValueError(f"Tag '{tag}' not found on model '{model_id}'.")
        tags.remove(tag)
        meta["tags"] = tags
        self._write_metadata(model_id, meta)

    def list_tags(self) -> Dict[str, List[str]]:
        """
        Return a reverse index: {tag: [model_ids]}.  v9 DoD #3.
        """
        tag_index: Dict[str, List[str]] = {}
        for model in self.list_models():
            for tag in model.get("tags", []):
                tag_index.setdefault(tag, []).append(model["id"])
        return tag_index

    def list_models_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """
        Return models that have the given tag, newest first.  v9 DoD #3.
        """
        return [m for m in self.list_models() if tag in m.get("tags", [])]

    def compare_models(self, model_id_1: str, model_id_2: str) -> Dict[str, Any]:
        """
        Compare accuracy and metadata of two registered models.  v9 DoD #3.

        Returns:
            {
              "model1": {metadata},
              "model2": {metadata},
              "differences": [
                  {"field": str, "value1": Any, "value2": Any,
                   "diff": float|None, "winner": str, "note": str}
              ]
            }

        Raises:
            FileNotFoundError: if either model_id not found.
        """
        m1 = self.get_metadata(model_id_1)
        m2 = self.get_metadata(model_id_2)

        differences: List[Dict[str, Any]] = []

        acc1 = m1.get("accuracy", m1.get("metrics", {}).get("test_accuracy", 0.0))
        acc2 = m2.get("accuracy", m2.get("metrics", {}).get("test_accuracy", 0.0))
        diff = round(acc1 - acc2, 4)
        if acc1 > acc2:
            winner, note = "model1", f"+{diff:.4f} (model1 leads)"
        elif acc2 > acc1:
            winner, note = "model2", f"{diff:.4f} (model2 leads)"
        else:
            winner, note = "tie", "identical accuracy"
        differences.append({
            "field": "test_accuracy",
            "value1": acc1, "value2": acc2,
            "diff": diff, "winner": winner, "note": note,
        })

        tr1 = m1.get("metrics", {}).get("train_accuracy", 0.0)
        tr2 = m2.get("metrics", {}).get("train_accuracy", 0.0)
        if tr1 != tr2:
            tr_diff = round(tr1 - tr2, 4)
            if tr1 > tr2:
                tr_winner, tr_note = "model1", f"+{tr_diff:.4f} (model1 leads)"
            elif tr2 > tr1:
                tr_winner, tr_note = "model2", f"{tr_diff:.4f} (model2 leads)"
            else:
                tr_winner, tr_note = "tie", "identical"
            differences.append({
                "field": "train_accuracy",
                "value1": tr1, "value2": tr2,
                "diff": tr_diff, "winner": tr_winner, "note": tr_note,
            })

        if m1.get("model_type") != m2.get("model_type"):
            differences.append({
                "field": "model_type",
                "value1": m1.get("model_type"),
                "value2": m2.get("model_type"),
                "diff": None, "winner": "tie",
                "note": "different model families",
            })

        p1 = m1.get("hyperparameters", {})
        p2 = m2.get("hyperparameters", {})
        common_keys = sorted(set(p1.keys()) & set(p2.keys()))
        for key in common_keys:
            if p1[key] != p2[key]:
                differences.append({
                    "field": f"hyperparameter:{key}",
                    "value1": p1[key], "value2": p2[key],
                    "diff": None, "winner": "tie", "note": "",
                })

        ds1 = m1.get("dataset", {}).get("name", "unknown")
        ds2 = m2.get("dataset", {}).get("name", "unknown")
        if ds1 != ds2:
            differences.append({
                "field": "dataset",
                "value1": ds1, "value2": ds2,
                "diff": None, "winner": "tie",
                "note": "⚠️ comparing across different datasets",
            })

        return {"model1": m1, "model2": m2, "differences": differences}

    # ── Benchmark Registry (v8 DoD #4) ─────────────────────────────────────────

    def save_benchmark(
        self,
        mode: str,
        results: list,
        summary: dict,
        duration_seconds: float,
        report_json: str = "",
        report_md: str = "",
        regression_details: list = None,
        git_hash: str = "unknown",
    ) -> str:
        """
        Persist a benchmark run to the registry.  v8 DoD #4.

        Returns:
            benchmark_id: str, e.g. "2026-06-07_xyz789"
        """
        self._ensure_dirs()

        date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        short_id = self._short_id()
        benchmark_id = f"{date_str}_{short_id}"

        json_path = self.benchmarks_dir / f"{benchmark_id}.json"

        metadata = BenchmarkMetadata(
            id=benchmark_id,
            mode=mode,
            timestamp=datetime.now(timezone.utc).isoformat(),
            duration_seconds=round(duration_seconds, 3),
            git_hash=git_hash,
            total_experiments=summary.get("total_experiments", len(results)),
            passed=summary.get("passed", 0),
            failed=summary.get("failed", 0),
            regressions=summary.get("regressions", 0),
            model_results=results,
            regression_details=regression_details or [],
            report_json=report_json,
            report_md=report_md,
        )

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(asdict(metadata), f, indent=2, ensure_ascii=False)

        return benchmark_id

    def list_benchmarks(self) -> List[Dict[str, Any]]:
        """
        Return metadata for all registered benchmark runs, newest first (by timestamp).
        """
        benchmarks = []
        for json_file in self.benchmarks_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    benchmarks.append(json.load(f))
            except Exception:
                continue
        benchmarks.sort(key=lambda b: b.get("timestamp", ""), reverse=True)
        return benchmarks

    def get_benchmark(self, benchmark_id: str) -> Dict[str, Any]:
        """
        Return full metadata for a specific benchmark run.
        Raises FileNotFoundError if not found.
        """
        json_path = self.benchmarks_dir / f"{benchmark_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Benchmark '{benchmark_id}' not found. Run 'ml-db benchmark list' to see available runs."
            )
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

    def get_latest_benchmark(self, mode: str = None) -> Optional[Dict[str, Any]]:
        """
        Return the most recent benchmark run, optionally filtered by mode.
        Returns None if no benchmark found.
        """
        benchmarks = self.list_benchmarks()
        if mode:
            benchmarks = [b for b in benchmarks if b.get("mode") == mode]
        return benchmarks[0] if benchmarks else None

    def detect_regressions(
        self,
        current_run_id: str = None,
        previous_run_id: str = None,
        threshold: float = REGRESSION_THRESHOLD,
    ) -> Dict[str, Any]:
        """
        Detect accuracy regressions between two benchmark runs.  v8 DoD #4.

        If current_run_id is None, uses the latest run.
        If previous_run_id is None, uses the second-latest run.

        A regression is flagged when a (model, dataset) pair shows accuracy
        drop > threshold fraction vs the previous run.

        Returns:
            dict with keys: has_regressions, count, details (list of regression records)
        """
        current_run = (
            self.get_benchmark(current_run_id)
            if current_run_id
            else self.get_latest_benchmark()
        )
        if not current_run:
            return {"has_regressions": False, "count": 0, "details": [], "error": "No current benchmark found"}

        # Collect all previous runs excluding current
        all_runs = self.list_benchmarks()
        previous_runs = [r for r in all_runs if r["id"] != current_run["id"]]
        if previous_run_id:
            previous_runs = [r for r in previous_runs if r["id"] == previous_run_id]

        previous_run = previous_runs[0] if previous_runs else None
        if not previous_run:
            return {"has_regressions": False, "count": 0, "details": [], "error": "No previous benchmark found"}

        # Build lookup: (model, dataset) -> accuracy
        def build_lookup(run):
            return {
                (r.get("model"), r.get("dataset")): r.get("accuracy")
                for r in run.get("model_results", [])
                if r.get("accuracy") is not None
            }

        current_lookup = build_lookup(current_run)
        previous_lookup = build_lookup(previous_run)

        details = []
        for (model, dataset), current_acc in current_lookup.items():
            prev_acc = previous_lookup.get((model, dataset))
            if prev_acc is None:
                continue
            if current_acc < prev_acc * (1 - threshold):
                details.append({
                    "model": model,
                    "dataset": dataset,
                    "current_accuracy": round(current_acc, 4),
                    "previous_accuracy": round(prev_acc, 4),
                    "drop": round(prev_acc - current_acc, 4),
                    "drop_pct": round((prev_acc - current_acc) / max(prev_acc, 1e-9) * 100, 2),
                })

        return {
            "has_regressions": len(details) > 0,
            "count": len(details),
            "details": details,
            "current_run_id": current_run["id"],
            "previous_run_id": previous_run["id"],
            "threshold": threshold,
        }


# ── Module-level singleton (lazy) ─────────────────────────────────────────────

_default_manager: Optional[RegistryManager] = None


def get_registry_manager() -> RegistryManager:
    """Get or create the default RegistryManager singleton."""
    global _default_manager
    if _default_manager is None:
        _default_manager = RegistryManager()
    return _default_manager
