"""
core/registry.py — Model Registry & Lifecycle Management

v8 DoD #1: Auto-registers training results to ~/.ml-decision-boundary/registry/
v8 DoD #2: save_model() / load_model() interfaces
v9 DoD #3: compare / tag / untag / list_tags / list_models_by_tag
v12 DoD #3: model versioning (v1/v2) + batch tag query (list_models_by_tags)

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
import os
import time
from pathlib import Path
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional, Sequence
from dataclasses import dataclass, asdict, field

from core.provenance import (
    build_provenance,
    build_replay_plan,
    provenance_diff,
)
from core.coverage import (
    coverage_summary,
    provenance_coverage,
    replayability_report,
)
from core.blob_store import BlobStore


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
    version: int = 1                             # v12 DoD #3: version within the model family
    family: str = ""                             # v12 DoD #3: family key (type+dataset+params)
    provenance: Dict[str, Any] = field(default_factory=dict)  # v13 DoD #1
    blob_digest: str = ""                        # v13 DoD #4: SHA-256 of the stored artifact


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
        # v13 DoD #4: content-addressed store for serialized models, so
        # re-running an identical experiment does not store a second copy.
        self.blobs = BlobStore(self.registry_base)
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

    # ── v12 DoD #3: Model versioning ───────────────────────────────────────────

    @staticmethod
    def family_key(
        model_type: str,
        dataset_name: str,
        hyperparameters: Dict[str, Any],
    ) -> str:
        """Build the stable family key a model belongs to.

        A family groups models that differ only by run (same model type,
        same dataset, same hyperparameters).  Re-training the same setup
        produces ``v2``, ``v3`` ... of that family.

        The key is deterministic: hyperparameter keys are sorted and values
        are rendered with ``repr`` so that ``{"C": 1.0}`` and
        ``{"C": 1}`` produce different families (they may train differently).
        """
        params = hyperparameters or {}
        parts = [str(model_type or "unknown"), str(dataset_name or "unknown")]
        for key in sorted(params.keys()):
            parts.append(f"{key}={params[key]!r}")
        return "|".join(parts)

    def _next_version(self, family: str) -> int:
        """Return the next version number for `family` (1 when unseen)."""
        if not family:
            return 1
        versions = [
            int(m.get("version", 1) or 1)
            for m in self.list_models()
            if m.get("family") == family
        ]
        return max(versions) + 1 if versions else 1

    def list_model_families(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return ``{family_key: [model metadata, ...]}`` grouped by family.

        Each family list is ordered by version ascending (v1 first).
        Families are returned newest-first by their latest member's
        ``created_at`` so that recent work surfaces at the top.
        """
        families: Dict[str, List[Dict[str, Any]]] = {}
        for model in self.list_models():
            key = model.get("family") or self._legacy_family(model)
            families.setdefault(key, []).append(model)
        for key, members in families.items():
            members.sort(key=lambda m: (int(m.get("version", 1) or 1), m.get("created_at", "")))
        return dict(
            sorted(
                families.items(),
                key=lambda kv: max((m.get("created_at", "") for m in kv[1]), default=""),
                reverse=True,
            )
        )

    @staticmethod
    def _legacy_family(model: Dict[str, Any]) -> str:
        """Derive the family key of a pre-v12 model (no ``family`` field)."""
        dataset = model.get("dataset")
        dataset_name = (
            dataset.get("name", "unknown") if isinstance(dataset, dict) else str(dataset or "unknown")
        )
        hyperparameters = model.get("hyperparameters")
        if not isinstance(hyperparameters, dict):
            hyperparameters = {}
        return RegistryManager.family_key(
            model.get("model_type", "unknown"),
            dataset_name,
            hyperparameters,
        )

    def get_model_versions(self, model_id: str) -> List[Dict[str, Any]]:
        """Return every version of the family that `model_id` belongs to.

        Raises:
            FileNotFoundError: if model_id is not registered.
        """
        meta = self.get_metadata(model_id)
        family = meta.get("family") or self._legacy_family(meta)
        versions = [
            m for m in self.list_models()
            if (m.get("family") or self._legacy_family(m)) == family
        ]
        versions.sort(key=lambda m: (int(m.get("version", 1) or 1), m.get("created_at", "")))
        return versions

    def get_latest_version(self, model_id: str) -> Dict[str, Any]:
        """Return the newest version of the family that `model_id` belongs to.

        Raises:
            FileNotFoundError: if model_id is not registered.
        """
        versions = self.get_model_versions(model_id)
        if not versions:
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        return versions[-1]

    # ── v12 DoD #3: Batch tag query ───────────────────────────────────────────

    def list_models_by_tags(
        self,
        tags: Sequence[str],
        mode: str = "any",
    ) -> List[Dict[str, Any]]:
        """Return models matching a batch of tags.

        Args:
            tags: tag names to match.
            mode: ``"any"`` (default) matches models carrying **at least one**
                of the tags; ``"all"`` matches models carrying **every** tag.

        Returns:
            Matching model metadata, newest first (same ordering as
            :meth:`list_models`).

        Raises:
            ValueError: if `mode` is not ``"any"`` or ``"all"``, or if
                `tags` is empty.
        """
        if mode not in ("any", "all"):
            raise ValueError(
                f"Invalid tag match mode '{mode}'. Expected 'any' or 'all'."
            )
        wanted = [t.strip() for t in (tags or []) if t and t.strip()]
        if not wanted:
            raise ValueError("At least one tag is required for a batch tag query.")

        result = []
        for model in self.list_models():
            model_tags = set(model.get("tags", []))
            if mode == "all":
                if model_tags.issuperset(wanted):
                    result.append(model)
            elif model_tags & set(wanted):
                result.append(model)
        return result

    def tag_index(self) -> Dict[str, List[str]]:
        """Return ``{tag: [model_id, ...]}`` with model ids newest-first.

        Canonical implementation of the reverse tag index; :meth:`list_tags`
        delegates here.  Within each bucket the ids are ordered by
        ``created_at`` descending (newest first), matching the ordering of
        :meth:`list_models`.
        """
        index: Dict[str, List[str]] = {}
        for model in self.list_models():
            for tag in model.get("tags", []):
                index.setdefault(tag, []).append(model["id"])
        return index

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
        provenance: Optional[Dict[str, Any]] = None,
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

        # v12 DoD #3: family key + next version number within that family
        family = self.family_key(model_type, dataset_name, hyperparameters)
        version = self._next_version(family)

        # Dataset hash
        dataset_hash = "unknown"
        if X_train is not None and y_train is not None:
            dataset_hash = self._dataset_hash(X_train, y_train)

        # Paths
        json_path = self.models_dir / f"{model_id}.json"

        # v13 DoD #4: store the serialized model content-addressed.  Two
        # runs with the same seed and hyperparameters produce byte-identical
        # artifacts, so the second one reuses the first one's blob instead
        # of writing a duplicate copy to disk.
        blob_digest = self.blobs.store_model(model)
        joblib_path = self.blobs.blob_path(blob_digest)

        # Build metadata
        provenance_record = provenance or build_provenance(
            seed=None,
            dataset_name=dataset_name,
            n_samples=n_samples,
            hyperparameters=hyperparameters,
            model_type=model_type,
        )
        # v13 DoD #2: freeze the replay recipe at registration time so the
        # exact recipe that reproduces *this* run is preserved alongside it.
        if isinstance(provenance_record, dict) and not provenance_record.get("replay"):
            provenance_record = dict(provenance_record)
            provenance_record["replay"] = build_replay_plan(provenance_record)

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
            blob_digest=blob_digest,
            accuracy=round(test_accuracy, 4),
            plugin_state=plugin_state,
            tags=[],  # v9 DoD #3: initialized empty
            version=version,       # v12 DoD #3
            family=family,         # v12 DoD #3
            provenance=provenance_record,
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
        """Return metadata dict for a model without loading the model object.

        Legacy models registered before v12 DoD #3 are normalized on read:
        ``version`` defaults to 1 and ``family`` is derived from the model's
        type / dataset / hyperparameters, so old registries keep working.
        """
        json_path = self.models_dir / f"{model_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        with open(json_path, encoding="utf-8") as f:
            metadata = json.load(f)
        return self._normalize(metadata)

    @classmethod
    def _normalize(cls, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """Fill in v12 DoD #3 fields that legacy metadata files lack."""
        metadata.setdefault("tags", [])
        metadata.setdefault("version", 1)
        if not metadata.get("family"):
            metadata["family"] = cls._legacy_family(metadata)
        metadata.setdefault("provenance", {})
        return metadata

    # ── v13 DoD #1: provenance ────────────────────────────────────────────────

    def get_provenance(self, model_id: str) -> Dict[str, Any]:
        """Return a model's provenance; legacy models return an empty dict."""
        metadata = self.get_metadata(model_id)
        return dict(metadata.get("provenance") or {})

    def compare_provenance(self, model_id_a: str, model_id_b: str) -> Dict[str, Any]:
        """Compare the provenance of two registered models."""
        result = provenance_diff(
            self.get_provenance(model_id_a),
            self.get_provenance(model_id_b),
        )
        result["left_model_id"] = model_id_a
        result["right_model_id"] = model_id_b
        return result

    # ── v13 DoD #2: reproducibility replay ────────────────────────────────────

    def get_replay_plan(self, model_id: str) -> Dict[str, Any]:
        """Return the replay recipe for a registered model.

        The stored provenance already carries the replay snapshot captured
        at registration time (DoD #2).  When it is absent — legacy models
        and models registered before DoD #2 — the plan is derived on the
        fly from the stored provenance, so the endpoint degrades gracefully
        instead of failing.

        Raises:
            FileNotFoundError: if `model_id` is not registered.
        """
        metadata = self.get_metadata(model_id)
        provenance = dict(metadata.get("provenance") or {})
        if not provenance:
            return {
                "model_id": model_id,
                "available": False,
                "reason": "model has no provenance record (registered before v13)",
                "sdk": None,
                "cli": None,
                "dependencies": None,
                "expected": None,
            }

        plan = dict(provenance.get("replay") or {})
        if not plan.get("sdk"):
            plan = build_replay_plan(provenance)
        plan["model_id"] = model_id
        plan["available"] = True
        return plan

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
                    models.append(self._normalize(json.load(f)))
            except Exception:
                # Skip corrupted metadata files
                continue
        # Sort by created_at descending (newest first)
        models.sort(key=lambda m: m.get("created_at", ""), reverse=True)
        return models

    # ── v13 DoD #3: provenance coverage ───────────────────────────────────────

    def provenance_coverage(self) -> Dict[str, Any]:
        """Audit how much of the registry carries usable provenance.

        Read-only: no metadata file is rewritten, so running the audit
        against a registry full of pre-v13 models is safe.

        Returns:
            A dict with ``summary`` (aggregated counters and percentages),
            ``report`` (non-reproducible models grouped by cause) and
            ``models`` (per-model classification, newest first).
        """
        models = self.list_models()

        # Models registered during DoD #1 have a provenance record but no
        # frozen replay snapshot; their plan is derivable on demand.  The
        # audit must count them the way ``get_replay_plan()`` would, so the
        # resolved plans are resolved up-front (and cached) here.
        replay_plans: Dict[str, Dict[str, Any]] = {}
        for model in models:
            provenance = model.get("provenance") or {}
            if not isinstance(provenance, dict) or not provenance:
                continue
            model_id = model.get("id") or model.get("model_id")
            if not model_id:
                continue
            try:
                plan = self.get_replay_plan(model_id)
            except Exception:
                continue
            if plan.get("available"):
                replay_plans[model_id] = plan

        return {
            "summary": coverage_summary(models, replay_plans),
            "report": replayability_report(models, replay_plans),
            "models": provenance_coverage(models, replay_plans),
        }

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
        blob_digest = metadata.get("blob_digest") or ""

        # v13 DoD #4: a blob may be shared by several models, so it is only
        # removed when the last model referencing it goes away.  Legacy
        # per-model files (no blob_digest) are removed as before.
        removed = False
        if blob_digest:
            if self._blob_reference_count(blob_digest) <= 1:
                removed = self.blobs.delete(blob_digest)
        elif joblib_path.exists():
            joblib_path.unlink()
            removed = True

        json_path.unlink()

    def _blob_reference_count(self, blob_digest: str) -> int:
        """Count how many registered models point at ``blob_digest``."""
        if not blob_digest:
            return 0
        count = 0
        for json_file in self.models_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    metadata = json.load(f)
            except (OSError, ValueError):
                continue
            if metadata.get("blob_digest") == blob_digest:
                count += 1
        return count

    def storage_stats(self) -> Dict[str, Any]:
        """Report how much disk the registry occupies and how much is shared.

        ``logical_bytes`` is the size every model *would* occupy with its
        own private copy; ``stored_bytes`` is what is actually on disk.
        The ratio between them is the deduplication gain.
        """
        blob_stats = self.blobs.stats()
        shared = 0
        per_model = 0
        referenced: Dict[str, int] = {}
        model_count = 0

        for json_file in self.models_dir.glob("*.json"):
            try:
                with open(json_file, encoding="utf-8") as f:
                    metadata = json.load(f)
            except (OSError, ValueError):
                continue
            model_count += 1
            digest = metadata.get("blob_digest")
            if digest:
                referenced[digest] = referenced.get(digest, 0) + 1
            else:
                path = self.registry_base / metadata.get("joblib_path", "")
                try:
                    per_model += path.stat().st_size
                except OSError:
                    pass

        # Shared blobs are counted once on disk but may be referenced N times.
        # Each reference would have cost a full private copy, so the logical
        # size is the sum over references, not over unique blobs.
        logical = 0
        for digest, count in referenced.items():
            path = self.blobs.blob_path(digest)
            try:
                logical += path.stat().st_size * count
            except OSError:
                pass
        logical += per_model

        stored = shared + per_model
        for digest in referenced:
            path = self.blobs.blob_path(digest)
            try:
                stored += path.stat().st_size
            except OSError:
                pass

        return {
            "models": model_count,
            "unique_blobs": len(referenced),
            "blob_files_on_disk": blob_stats["blob_count"],
            "stored_bytes": stored,
            "logical_bytes": logical,
            "dedup_saved_bytes": max(logical - stored, 0),
            "dedup_ratio": (logical / stored) if stored else 1.0,
            "legacy_per_model_bytes": per_model,
        }

    # ── CLI helpers ────────────────────────────────────────────────────────────

    def find_model(self, model_id: str) -> bool:
        """Return True if model_id exists in registry."""
        return (self.models_dir / f"{model_id}.json").exists()

    # ── v9 DoD #3: Tags & Compare ──────────────────────────────────────────────

    def _read_raw_metadata(self, model_id: str) -> Dict[str, Any]:
        """Return the metadata dict exactly as stored on disk (no normalization).

        Used by mutating operations (tag/untag) so that legacy pre-v12
        metadata files are not silently migrated: only the field the caller
        actually changes is written back.
        """
        json_path = self.models_dir / f"{model_id}.json"
        if not json_path.exists():
            raise FileNotFoundError(
                f"Model '{model_id}' not found. Run 'ml-db model list'."
            )
        with open(json_path, encoding="utf-8") as f:
            return json.load(f)

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
        # Read raw (un-normalized) metadata: tagging must not rewrite the
        # other fields of a legacy pre-v12 metadata file.  v12 DoD #3.
        meta = self._read_raw_metadata(model_id)
        tags: List[str] = list(meta.get("tags", []))
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
        # Read raw (un-normalized) metadata — see tag_model().  v12 DoD #3.
        meta = self._read_raw_metadata(model_id)
        tags: List[str] = list(meta.get("tags", []))
        if tag not in tags:
            raise ValueError(f"Tag '{tag}' not found on model '{model_id}'.")
        tags.remove(tag)
        meta["tags"] = tags
        self._write_metadata(model_id, meta)

    def list_tags(self) -> Dict[str, List[str]]:
        """
        Return a reverse index: {tag: [model_ids]}.  v9 DoD #3.

        Alias of :meth:`tag_index` (v12 DoD #3) — kept for backward
        compatibility with the v9 CLI/SDK surface.
        """
        return self.tag_index()

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
    """Get or create the default RegistryManager singleton.

    The registry root can be redirected with the ``MLDB_REGISTRY_BASE``
    environment variable (used by the CLI, the local Flask server and tests
    to work against a scratch registry instead of the user's real one).
    """
    global _default_manager
    if _default_manager is None:
        base = os.environ.get("MLDB_REGISTRY_BASE")
        _default_manager = RegistryManager(Path(base) if base else REGISTRY_BASE)
    return _default_manager
