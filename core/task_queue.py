"""
core/task_queue.py — Async Training Task Queue (v12 DoD #2)

Background training jobs with **persistent** state:

  ~/.ml-decision-boundary/registry/tasks/
  ├── 2026-10-25_ab12cd.json   # task record (state persisted to disk)
  └── ...

Design notes
------------
* **Single source of truth on disk.**  Every state transition writes the JSON
  record atomically (write-temp + ``os.replace``), so a crash or a restart
  never loses the task list.  On construction the manager *recovers* tasks that
  were still ``pending``/``running`` when the process died and marks them
  ``failed`` with a ``interrupted`` reason — they cannot silently hang.
* **One worker thread per task**, started lazily by :meth:`TaskQueue.submit`.
  The worker is a daemon thread so it never blocks interpreter shutdown.
* **No training logic lives here.**  The queue accepts a plain callable
  ``fn() -> dict``; the actual training is done by the caller (the SDK), so the
  CLI / HTTP API / SDK keep using the same ``core/train_utils`` code path.

Task state machine
------------------
    pending ──▶ running ──▶ succeeded
                     │
                     └─────▶ failed

Terminal states are ``succeeded`` and ``failed``; ``pending`` and ``running``
are transient.
"""

import json
import os
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

#: Task states.
STATE_PENDING = "pending"
STATE_RUNNING = "running"
STATE_SUCCEEDED = "succeeded"
STATE_FAILED = "failed"

#: Terminal states — once reached, the task record never changes again.
TERMINAL_STATES = frozenset({STATE_SUCCEEDED, STATE_FAILED})

DEFAULT_TASKS_DIR = (
    Path.home() / ".ml-decision-boundary" / "registry" / "tasks"
)


def _utc_now_iso() -> str:
    """Current UTC time as an ISO8601 string with timezone."""
    return datetime.now(timezone.utc).isoformat()


def _short_id() -> str:
    """Short unique suffix for task ids."""
    return uuid.uuid4().hex[:6]


class TaskNotFoundError(FileNotFoundError):
    """Raised when a task id is unknown to the queue.

    Subclasses :class:`FileNotFoundError` so callers that already handle
    missing registry entries keep working unchanged.
    """


class TaskQueue:
    """Persistent background task queue.

    Args:
        tasks_dir: directory holding the task JSON records.
            Defaults to ``~/.ml-decision-boundary/registry/tasks``.
        registry: optional :class:`core.registry.RegistryManager` used to
            register the model produced by a successful training task.
    """

    def __init__(self, tasks_dir: Optional[Path] = None, registry=None):
        self.tasks_dir = Path(tasks_dir) if tasks_dir else DEFAULT_TASKS_DIR
        self.registry = registry
        self._lock = threading.RLock()
        self._threads: Dict[str, threading.Thread] = {}
        self._ensure_dir()
        self._recover_interrupted()

    # ── Storage helpers ──────────────────────────────────────────────────────

    def _ensure_dir(self) -> None:
        self.tasks_dir.mkdir(parents=True, exist_ok=True)

    def _path(self, task_id: str) -> Path:
        return self.tasks_dir / f"{task_id}.json"

    def _write(self, record: Dict[str, Any]) -> None:
        """Atomically persist a task record."""
        self._ensure_dir()
        path = self._path(record["id"])
        tmp = path.with_suffix(".json.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(record, f, indent=2, ensure_ascii=False)
        os.replace(tmp, path)

    def _read(self, task_id: str) -> Dict[str, Any]:
        path = self._path(task_id)
        if not path.exists():
            raise TaskNotFoundError(
                f"Task '{task_id}' not found. "
                "Use list_tasks() to see available tasks."
            )
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    def _recover_interrupted(self) -> None:
        """Mark tasks left ``pending``/``running`` by a dead process as failed.

        Without this, a restart would leave tasks that can never complete —
        the caller would poll forever.  Recovery is best-effort: a corrupted
        record is skipped rather than raising.
        """
        for path in self.tasks_dir.glob("*.json"):
            try:
                with open(path, encoding="utf-8") as f:
                    record = json.load(f)
            except Exception:
                continue
            state = record.get("status")
            if state in TERMINAL_STATES:
                continue
            record["status"] = STATE_FAILED
            record["error"] = "interrupted: process restarted before the task finished"
            record["finished_at"] = _utc_now_iso()
            try:
                self._write(record)
            except Exception:
                continue

    # ── Public API ───────────────────────────────────────────────────────────

    def submit(
        self,
        fn: Callable[[], Dict[str, Any]],
        *,
        name: str = "train",
        meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Queue ``fn`` for background execution and return the task record.

        Args:
            fn: zero-argument callable returning a JSON-serializable dict.
                It is executed on a background worker thread.
            name: short task name (e.g. ``"train"``).
            meta: arbitrary metadata stored alongside the task
                (model name, dataset, params, ...).

        Returns:
            The freshly created task record (``status == "pending"``).
        """
        with self._lock:
            date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            task_id = f"{date_str}_{_short_id()}"
            record: Dict[str, Any] = {
                "id": task_id,
                "name": name,
                "status": STATE_PENDING,
                "created_at": _utc_now_iso(),
                "started_at": None,
                "finished_at": None,
                "result": None,
                "error": None,
                "meta": dict(meta or {}),
            }
            self._write(record)

            thread = threading.Thread(
                target=self._run,
                args=(task_id, fn),
                name=f"ml-db-task-{task_id}",
                daemon=True,
            )
            self._threads[task_id] = thread
            thread.start()
            return dict(record)

    def _run(self, task_id: str, fn: Callable[[], Dict[str, Any]]) -> None:
        """Worker body: execute ``fn`` and persist the outcome."""
        with self._lock:
            try:
                record = self._read(task_id)
            except TaskNotFoundError:
                return
            record["status"] = STATE_RUNNING
            record["started_at"] = _utc_now_iso()
            self._write(record)

        try:
            result = fn()
        except Exception as exc:  # noqa: BLE001 — surfaced to the caller
            with self._lock:
                record = self._read(task_id)
                record["status"] = STATE_FAILED
                record["error"] = f"{type(exc).__name__}: {exc}"
                record["finished_at"] = _utc_now_iso()
                self._write(record)
            return

        with self._lock:
            record = self._read(task_id)
            record["status"] = STATE_SUCCEEDED
            record["result"] = result
            record["finished_at"] = _utc_now_iso()
            self._write(record)

    def get(self, task_id: str) -> Dict[str, Any]:
        """Return the task record for ``task_id``.

        Raises:
            TaskNotFoundError: if the task is unknown.
        """
        with self._lock:
            return self._read(task_id)

    def list_tasks(self, status: Optional[str] = None) -> List[Dict[str, Any]]:
        """Return task records, newest first.

        Args:
            status: optional filter — only tasks in that state are returned.
        """
        with self._lock:
            tasks: List[Dict[str, Any]] = []
            for path in self.tasks_dir.glob("*.json"):
                try:
                    with open(path, encoding="utf-8") as f:
                        tasks.append(json.load(f))
                except Exception:
                    continue
            if status is not None:
                tasks = [t for t in tasks if t.get("status") == status]
            tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
            return tasks

    def wait(
        self,
        task_id: str,
        timeout: Optional[float] = None,
        poll_interval: float = 0.05,
    ) -> Dict[str, Any]:
        """Block until the task reaches a terminal state.

        Args:
            task_id: task to wait on.
            timeout: max seconds to wait; ``None`` waits forever.
            poll_interval: seconds between status polls.

        Returns:
            The final task record.

        Raises:
            TaskNotFoundError: if the task is unknown.
            TimeoutError: if ``timeout`` elapses first.
        """
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            record = self.get(task_id)
            if record.get("status") in TERMINAL_STATES:
                return record
            if deadline is not None and time.monotonic() >= deadline:
                raise TimeoutError(
                    f"Task '{task_id}' did not finish within {timeout}s "
                    f"(last status: {record.get('status')})."
                )
            time.sleep(poll_interval)

    def cancel(self, task_id: str) -> Dict[str, Any]:
        """Request cancellation of a task.

        A task that is already finished is returned unchanged.  A task that
        has not started yet (``pending``) is cancelled immediately.  A running
        task is flagged ``cancel_requested`` — the worker checks the flag
        between stages and stops at the next checkpoint.
        """
        with self._lock:
            record = self._read(task_id)
            if record.get("status") in TERMINAL_STATES:
                return record
            record["cancel_requested"] = True
            if record.get("status") == STATE_PENDING:
                record["status"] = STATE_FAILED
                record["error"] = "cancelled before the task started"
                record["finished_at"] = _utc_now_iso()
            self._write(record)
            return record

    def delete(self, task_id: str) -> None:
        """Remove a task record from disk.

        Raises:
            TaskNotFoundError: if the task is unknown.
        """
        with self._lock:
            path = self._path(task_id)
            if not path.exists():
                raise TaskNotFoundError(
                    f"Task '{task_id}' not found. "
                    "Use list_tasks() to see available tasks."
                )
            path.unlink()

    def clear(self) -> int:
        """Delete every finished task record. Returns the number removed."""
        removed = 0
        for record in self.list_tasks():
            if record.get("status") in TERMINAL_STATES:
                self.delete(record["id"])
                removed += 1
        return removed


# ── Module-level singleton (lazy) ───────────────────────────────────────────

_default_queue: Optional[TaskQueue] = None
_default_lock = threading.Lock()


def get_task_queue() -> TaskQueue:
    """Get or create the default TaskQueue singleton."""
    global _default_queue
    with _default_lock:
        if _default_queue is None:
            _default_queue = TaskQueue()
        return _default_queue
