"""
ml_db/client.py — MLDB client object (v12 DoD #1)

The SDK is a thin wrapper over the existing `core/` layer:
  * training  → core.datasets + core.train_utils
  * registry  → core.registry.RegistryManager
No training logic is duplicated, so CLI / HTTP API / SDK always agree.

Quick start:

    from ml_db import MLDB

    db = MLDB()
    result = db.train(model="SVM", dataset="circles")
    print(result.model_id, result.accuracy)
    preds = db.predict(result.model_id, X=[[0.0, 0.0], [1.0, 1.0]])
"""

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Union

import numpy as np
from sklearn.model_selection import train_test_split

from core.datasets import DATASET_GENERATORS
from core.registry import RegistryManager
from core.task_queue import TaskNotFoundError, TaskQueue
from core.train_utils import BUILTIN_MODEL_NAMES, build_model
from ml_db.errors import (
    InvalidInputError,
    ModelNotFoundError,
    TaskNotFoundError as SDKTaskNotFoundError,
    UnknownDatasetError,
    UnknownModelError,
)

__all__ = ["MLDB", "TrainResult"]


@dataclass
class TrainResult:
    """Outcome of a single training run.

    Attributes:
        model_id: registry id (e.g. "2026-10-25_abc123"); empty when register=False
        model_type: model family used ("SVM", "RF", ...)
        dataset: dataset name used ("circles", ...)
        accuracy: test accuracy in [0, 1]
        train_accuracy: train accuracy in [0, 1]
        train_time: wall-clock seconds spent in `model.fit`
        params: resolved hyperparameters
        metadata: registry metadata dict (empty when register=False)
        model: the fitted estimator (not persisted; use model_id to reload)
    """

    model_id: str = ""
    model_type: str = ""
    dataset: str = ""
    accuracy: float = 0.0
    train_accuracy: float = 0.0
    train_time: float = 0.0
    params: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    model: Any = None

    def to_dict(self) -> Dict[str, Any]:
        """JSON-serializable view of the result (the estimator is omitted)."""
        return {
            "model_id": self.model_id,
            "model_type": self.model_type,
            "dataset": self.dataset,
            "accuracy": self.accuracy,
            "train_accuracy": self.train_accuracy,
            "train_time": self.train_time,
            "params": dict(self.params),
            "metadata": dict(self.metadata),
        }


class MLDB:
    """Python SDK entry point for ml-decision-boundary.

    Args:
        registry_base: override the registry root (defaults to
            `~/.ml-decision-boundary/registry`). Useful for tests.
        seed: default random seed for dataset generation and train/test split.
    """

    def __init__(
        self,
        registry_base: Optional[Union[str, Path]] = None,
        seed: int = 42,
        tasks_dir: Optional[Union[str, Path]] = None,
    ):
        """Create an SDK client.

        Args:
            registry_base: override the registry root (defaults to
                `~/.ml-decision-boundary/registry`). Useful for tests.
            seed: default random seed for dataset generation and train/test split.
            tasks_dir: override the async-task directory (defaults to
                `<registry_base>/tasks`). Useful for tests.
        """
        self.seed = seed
        self.registry = (
            RegistryManager(Path(registry_base)) if registry_base else RegistryManager()
        )
        if tasks_dir is not None:
            self.tasks = TaskQueue(Path(tasks_dir), registry=self.registry)
        else:
            self.tasks = TaskQueue(self.registry.registry_base / "tasks", registry=self.registry)

    # ── Introspection ─────────────────────────────────────────────────────────

    @staticmethod
    def datasets() -> List[str]:
        """Names of all available synthetic datasets."""
        return sorted(DATASET_GENERATORS.keys())

    @staticmethod
    def models() -> List[str]:
        """Names of all available builtin model types."""
        return list(BUILTIN_MODEL_NAMES)

    def dataset(
        self,
        name: str,
        n_samples: int = 500,
        noise: float = 0.3,
        seed: Optional[int] = None,
    ):
        """Return the raw ``(X, y)`` pair for a dataset.

        Raises:
            UnknownDatasetError: if `name` is not a known dataset.
        """
        if name not in DATASET_GENERATORS:
            raise UnknownDatasetError(name, self.datasets())
        return DATASET_GENERATORS[name](n_samples, noise, seed=self.seed if seed is None else seed)

    # ── Training ──────────────────────────────────────────────────────────────

    def train(
        self,
        model: str = "SVM",
        dataset: str = "circles",
        params: Optional[Dict[str, Any]] = None,
        n_samples: int = 500,
        noise: float = 0.3,
        test_size: float = 0.2,
        register: bool = True,
        tags: Optional[Sequence[str]] = None,
    ) -> TrainResult:
        """Train a model, evaluate it, and (by default) register it.

        Args:
            model: model family, e.g. "SVM", "RF", "Tree".
            dataset: dataset name, see `MLDB.datasets()`.
            params: hyperparameter overrides (defaults to sklearn defaults).
            n_samples: number of synthetic points to generate.
            noise: dataset noise level.
            test_size: fraction held out for evaluation.
            register: persist the fitted model into the registry.
            tags: optional tags to attach to the registered model.

        Returns:
            TrainResult

        Raises:
            UnknownDatasetError / UnknownModelError / InvalidInputError
        """
        if dataset not in DATASET_GENERATORS:
            raise UnknownDatasetError(dataset, self.datasets())
        if not 0.0 < test_size < 1.0:
            raise InvalidInputError(f"test_size must be in (0, 1), got {test_size}.")
        if n_samples < 2:
            raise InvalidInputError(f"n_samples must be >= 2, got {n_samples}.")

        model_type = model
        if model_type not in BUILTIN_MODEL_NAMES:
            # Unknown to the SDK list — let build_model raise the canonical error
            # (it also knows about plugin-provided models).
            try:
                build_model(model_type, dict(params or {}))
            except ValueError:
                raise UnknownModelError(model_type, self.models()) from None

        X, y = self.dataset(dataset, n_samples=n_samples, noise=noise)
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=test_size, random_state=self.seed
        )

        resolved_params = dict(params or {})
        estimator = build_model(model_type, resolved_params)

        t0 = time.perf_counter()
        estimator.fit(X_train, y_train)
        train_time = time.perf_counter() - t0

        train_accuracy = float(estimator.score(X_train, y_train))
        test_accuracy = float(estimator.score(X_test, y_test))

        result = TrainResult(
            model_type=model_type,
            dataset=dataset,
            accuracy=test_accuracy,
            train_accuracy=train_accuracy,
            train_time=train_time,
            params=resolved_params,
            model=estimator,
        )

        if register:
            model_id = self.registry.save_model(
                estimator,
                model_type=model_type,
                hyperparameters=resolved_params,
                X_train=X_train,
                y_train=y_train,
                X_test=X_test,
                y_test=y_test,
                dataset_name=dataset,
                n_samples=n_samples,
                train_accuracy=train_accuracy,
                test_accuracy=test_accuracy,
            )
            for tag in tags or []:
                self.registry.tag_model(model_id, tag)
            result.model_id = model_id
            result.metadata = self.registry.get_metadata(model_id)

        return result

    # ── Async training (v12 DoD #2) ───────────────────────────────────────────

    def train_async(
        self,
        model: str = "SVM",
        dataset: str = "circles",
        params: Optional[Dict[str, Any]] = None,
        n_samples: int = 500,
        noise: float = 0.3,
        test_size: float = 0.2,
        register: bool = True,
        tags: Optional[Sequence[str]] = None,
    ) -> Dict[str, Any]:
        """Start a background training job and return the task record.

        The job runs on a worker thread; poll :meth:`get_task` (or use
        :meth:`wait_for_task`) to follow its progress.  Task state is
        persisted to disk, so it survives a process restart.

        Args:
            model: model family, e.g. "SVM", "RF", "Tree".
            dataset: dataset name, see `MLDB.datasets()`.
            params: hyperparameter overrides (defaults to sklearn defaults).
            n_samples: number of synthetic points to generate.
            noise: dataset noise level.
            test_size: fraction held out for evaluation.
            register: persist the fitted model into the registry.
            tags: optional tags to attach to the registered model.

        Returns:
            Task record dict with keys ``id``, ``status``, ``created_at``, ...

        Raises:
            UnknownDatasetError / UnknownModelError / InvalidInputError —
            validated eagerly so a bad request fails fast, not in the worker.
        """
        # Validate eagerly — the caller gets an immediate, actionable error
        # instead of a failed task several seconds later.
        if dataset not in DATASET_GENERATORS:
            raise UnknownDatasetError(dataset, self.datasets())
        if not 0.0 < test_size < 1.0:
            raise InvalidInputError(f"test_size must be in (0, 1), got {test_size}.")
        if n_samples < 2:
            raise InvalidInputError(f"n_samples must be >= 2, got {n_samples}.")
        if model not in BUILTIN_MODEL_NAMES:
            try:
                build_model(model, dict(params or {}))
            except ValueError:
                raise UnknownModelError(model, self.models()) from None

        kwargs = dict(
            model=model,
            dataset=dataset,
            params=dict(params or {}),
            n_samples=n_samples,
            noise=noise,
            test_size=test_size,
            register=register,
            tags=list(tags or []),
        )

        def _job() -> Dict[str, Any]:
            result = self.train(**kwargs)
            return result.to_dict()

        return self.tasks.submit(
            _job,
            name="train",
            meta={
                "model": model,
                "dataset": dataset,
                "params": dict(params or {}),
                "n_samples": n_samples,
                "noise": noise,
                "test_size": test_size,
                "register": register,
                "tags": list(tags or []),
            },
        )

    def get_task(self, task_id: str) -> Dict[str, Any]:
        """Return the current state of a background task.

        Raises:
            TaskNotFoundError: if the task id is unknown.
        """
        try:
            return self.tasks.get(task_id)
        except TaskNotFoundError as exc:
            raise SDKTaskNotFoundError(task_id) from exc

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """List background tasks, newest first (optionally filtered by state)."""
        return self.tasks.list_tasks(status=status)

    def wait_for_task(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.05,
    ) -> Dict[str, Any]:
        """Block until a background task finishes and return its final record.

        Args:
            task_id: task to wait on.
            timeout: max seconds to wait; ``None`` waits forever.
            poll_interval: seconds between status polls.

        Raises:
            TaskNotFoundError: if the task id is unknown.
            TimeoutError: if the task does not finish within ``timeout``.
        """
        try:
            return self.tasks.wait(
                task_id, timeout=timeout, poll_interval=poll_interval
            )
        except TaskNotFoundError as exc:
            raise SDKTaskNotFoundError(task_id) from exc

    def cancel_task(self, task_id: str) -> Dict[str, Any]:
        """Request cancellation of a background task.

        Raises:
            TaskNotFoundError: if the task id is unknown.
        """
        try:
            return self.tasks.cancel(task_id)
        except TaskNotFoundError as exc:
            raise SDKTaskNotFoundError(task_id) from exc

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict(
        self,
        model_id: Optional[str] = None,
        X: Optional[Sequence[Sequence[float]]] = None,
        model: Any = None,
    ) -> List[Any]:
        """Predict labels for a batch of 2D points.

        Exactly one of `model_id` (registered model) or `model` (a fitted
        estimator) must be supplied.

        Raises:
            InvalidInputError: if no estimator could be resolved or X is invalid.
            ModelNotFoundError: if `model_id` is unknown to the registry.
        """
        estimator = self._resolve_model(model_id, model)
        points = self._validate_points(X)
        preds = estimator.predict(points)
        return preds.tolist() if hasattr(preds, "tolist") else list(preds)

    def predict_batch(
        self,
        model_id: Optional[str] = None,
        X: Optional[Sequence[Sequence[float]]] = None,
        model: Any = None,
    ) -> Dict[str, Any]:
        """Batch prediction with a structured response.

        Returns:
            {"predictions": [...], "count": int, "model_id": str|None}
        """
        predictions = self.predict(model_id=model_id, X=X, model=model)
        return {
            "predictions": predictions,
            "count": len(predictions),
            "model_id": model_id,
        }

    def _resolve_model(self, model_id: Optional[str], model: Any):
        if model is not None and model_id:
            raise InvalidInputError("Pass either model_id or model, not both.")
        if model is not None:
            if not hasattr(model, "predict"):
                raise InvalidInputError("`model` must expose a .predict() method.")
            return model
        if not model_id:
            raise InvalidInputError(
                "Provide `model_id` (registered model) or `model` (fitted estimator)."
            )
        try:
            return self.registry.load_model(model_id)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id) from exc

    @staticmethod
    def _validate_points(X: Optional[Sequence[Sequence[float]]]) -> np.ndarray:
        if X is None:
            raise InvalidInputError("`X` is required: a sequence of 2D points.")
        points = np.asarray(X, dtype=float)
        if points.ndim != 2 or points.shape[1] != 2:
            raise InvalidInputError(
                f"`X` must be a 2D array of shape (n_samples, 2), got {points.shape}."
            )
        if points.shape[0] == 0:
            raise InvalidInputError("`X` must contain at least one point.")
        return points

    # ── Registry passthrough ──────────────────────────────────────────────────

    def list_models(self) -> List[Dict[str, Any]]:
        """Metadata for every registered model, newest first."""
        return self.registry.list_models()

    def get_model(self, model_id: str) -> Dict[str, Any]:
        """Metadata for one registered model."""
        try:
            return self.registry.get_metadata(model_id)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id) from exc

    def load_model(self, model_id: str) -> Any:
        """Load a registered estimator object."""
        try:
            return self.registry.load_model(model_id)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id) from exc

    def tag(self, model_id: str, tag: str) -> None:
        """Attach a tag to a registered model."""
        try:
            self.registry.tag_model(model_id, tag)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id) from exc

    def untag(self, model_id: str, tag: str) -> None:
        """Remove a tag from a registered model."""
        try:
            self.registry.untag_model(model_id, tag)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id) from exc

    def list_tags(self) -> Dict[str, List[str]]:
        """Map of tag → model ids."""
        return self.registry.list_tags()

    def list_models_by_tag(self, tag: str) -> List[Dict[str, Any]]:
        """Metadata for all models carrying `tag`."""
        return self.registry.list_models_by_tag(tag)

    def compare(self, model_id_1: str, model_id_2: str) -> Dict[str, Any]:
        """Compare two registered models (accuracy, dataset, tags, ...)."""
        try:
            return self.registry.compare_models(model_id_1, model_id_2)
        except FileNotFoundError as exc:
            raise ModelNotFoundError(model_id_1) from exc
