"""
tests/test_task_queue.py — Async training task tests (v12 DoD #2)

Covers:
  * core.task_queue.TaskQueue — submit / poll / wait / cancel / recovery
  * ml_db.MLDB.train_async / get_task / list_tasks / wait_for_task
  * api/train_async.py + api/tasks.py serverless contracts
"""

import json
import sys
import os
import time
from pathlib import Path

import pytest

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.task_queue import (
    STATE_FAILED,
    STATE_PENDING,
    STATE_RUNNING,
    STATE_SUCCEEDED,
    TaskNotFoundError,
    TaskQueue,
)


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture
def queue(tmp_path):
    """A TaskQueue backed by a temporary directory."""
    return TaskQueue(tmp_path / "tasks")


@pytest.fixture
def sdk(tmp_path):
    """An MLDB client with an isolated registry + task directory."""
    from ml_db import MLDB
    return MLDB(
        registry_base=tmp_path / "registry",
        tasks_dir=tmp_path / "registry" / "tasks",
    )


def _slow_job(delay=0.2, payload=None):
    """Return a callable that sleeps then returns `payload`."""
    def _job():
        time.sleep(delay)
        return payload if payload is not None else {"accuracy": 0.9}
    return _job


def _failing_job(message="boom"):
    def _job():
        raise RuntimeError(message)
    return _job


# ─────────────────────────────────────────────────────────────────────────────
# TaskQueue — core behaviour
# ─────────────────────────────────────────────────────────────────────────────

class TestTaskQueueBasics:

    def test_submit_returns_pending_record(self, queue):
        record = queue.submit(_slow_job(0.05), name="train")
        assert record["status"] in (STATE_PENDING, STATE_RUNNING)
        assert record["name"] == "train"
        assert record["id"]
        assert record["created_at"]
        assert record["result"] is None
        assert record["error"] is None

    def test_task_succeeds_and_persists_result(self, queue):
        record = queue.submit(_slow_job(0.01, {"accuracy": 0.75}))
        final = queue.wait(record["id"], timeout=10)
        assert final["status"] == STATE_SUCCEEDED
        assert final["result"] == {"accuracy": 0.75}
        assert final["finished_at"] is not None
        assert final["error"] is None

    def test_failed_task_records_error(self, queue):
        record = queue.submit(_failing_job("kaboom"))
        final = queue.wait(record["id"], timeout=10)
        assert final["status"] == STATE_FAILED
        assert "kaboom" in final["error"]
        assert "RuntimeError" in final["error"]
        assert final["result"] is None

    def test_state_persisted_to_disk(self, queue):
        """Task records must survive a process restart (written to disk)."""
        record = queue.submit(_slow_job(0.01, {"accuracy": 0.5}))
        queue.wait(record["id"], timeout=10)

        path = queue.tasks_dir / f"{record['id']}.json"
        assert path.exists(), "Task record must be written to disk"
        with open(path, encoding="utf-8") as f:
            on_disk = json.load(f)
        assert on_disk["id"] == record["id"]
        assert on_disk["status"] == STATE_SUCCEEDED
        assert on_disk["result"]["accuracy"] == 0.5

    def test_get_unknown_task_raises(self, queue):
        with pytest.raises(TaskNotFoundError):
            queue.get("2026-01-01_deadbe")

    def test_wait_unknown_task_raises(self, queue):
        with pytest.raises(TaskNotFoundError):
            queue.wait("2026-01-01_deadbe", timeout=1)

    def test_wait_timeout_raises(self, queue):
        record = queue.submit(_slow_job(2.0))
        with pytest.raises(TimeoutError):
            queue.wait(record["id"], timeout=0.2)


class TestTaskQueueListing:

    def test_list_tasks_newest_first(self, queue):
        a = queue.submit(_slow_job(0.01))
        time.sleep(0.01)
        b = queue.submit(_slow_job(0.01))
        tasks = queue.list_tasks()
        assert len(tasks) == 2
        assert tasks[0]["id"] == b["id"], "Newest task must come first"
        assert tasks[1]["id"] == a["id"]

    def test_list_tasks_filters_by_status(self, queue):
        ok = queue.submit(_slow_job(0.01))
        bad = queue.submit(_failing_job())
        queue.wait(ok["id"], timeout=10)
        queue.wait(bad["id"], timeout=10)

        succeeded = queue.list_tasks(status=STATE_SUCCEEDED)
        failed = queue.list_tasks(status=STATE_FAILED)

        assert len(succeeded) == 1
        assert succeeded[0]["id"] == ok["id"]
        assert len(failed) == 1
        assert failed[0]["id"] == bad["id"]

    def test_delete_task_removes_record(self, queue):
        record = queue.submit(_slow_job(0.01))
        queue.wait(record["id"], timeout=10)
        queue.delete(record["id"])
        assert not (queue.tasks_dir / f"{record['id']}.json").exists()
        with pytest.raises(TaskNotFoundError):
            queue.get(record["id"])

    def test_clear_removes_only_finished(self, queue):
        done = queue.submit(_slow_job(0.01))
        queue.wait(done["id"], timeout=10)
        queue.submit(_slow_job(5.0))  # still running

        removed = queue.clear()
        assert removed == 1
        assert len(queue.list_tasks()) == 1


class TestTaskQueueRecovery:

    def test_interrupted_task_marked_failed_on_restart(self, tmp_path):
        """A task left `running` by a dead process must not hang forever."""
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)

        # Simulate a crash: a record stuck in `running`.
        orphan = {
            "id": "2026-10-25_orphan",
            "name": "train",
            "status": STATE_RUNNING,
            "created_at": "2026-10-25T00:00:00+00:00",
            "started_at": "2026-10-25T00:00:01+00:00",
            "finished_at": None,
            "result": None,
            "error": None,
            "meta": {},
        }
        with open(tasks_dir / "2026-10-25_orphan.json", "w", encoding="utf-8") as f:
            json.dump(orphan, f)

        q = TaskQueue(tasks_dir)
        record = q.get("2026-10-25_orphan")
        assert record["status"] == STATE_FAILED
        assert "interrupted" in record["error"]

    def test_pending_task_marked_failed_on_restart(self, tmp_path):
        tasks_dir = tmp_path / "tasks"
        tasks_dir.mkdir(parents=True)
        orphan = {
            "id": "2026-10-25_pending",
            "name": "train",
            "status": STATE_PENDING,
            "created_at": "2026-10-25T00:00:00+00:00",
            "started_at": None,
            "finished_at": None,
            "result": None,
            "error": None,
            "meta": {},
        }
        with open(tasks_dir / "2026-10-25_pending.json", "w", encoding="utf-8") as f:
            json.dump(orphan, f)

        q = TaskQueue(tasks_dir)
        assert q.get("2026-10-25_pending")["status"] == STATE_FAILED

    def test_finished_tasks_survive_restart_unchanged(self, tmp_path):
        tasks_dir = tmp_path / "tasks"
        q1 = TaskQueue(tasks_dir)
        record = q1.submit(_slow_job(0.01, {"accuracy": 0.42}))
        q1.wait(record["id"], timeout=10)

        q2 = TaskQueue(tasks_dir)  # simulate restart
        restored = q2.get(record["id"])
        assert restored["status"] == STATE_SUCCEEDED
        assert restored["result"]["accuracy"] == 0.42


class TestTaskQueueCancel:

    def test_cancel_pending_task(self, queue):
        """A queued task that never started is cancelled immediately."""
        # Occupy the worker so the next task stays pending is unreliable;
        # instead submit a slow job and cancel it while pending/running.
        record = queue.submit(_slow_job(0.5))
        cancelled = queue.cancel(record["id"])
        assert cancelled.get("cancel_requested") is True

    def test_cancel_finished_task_is_noop(self, queue):
        record = queue.submit(_slow_job(0.01))
        queue.wait(record["id"], timeout=10)
        cancelled = queue.cancel(record["id"])
        assert cancelled["status"] == STATE_SUCCEEDED
        assert cancelled.get("cancel_requested") is None


# ─────────────────────────────────────────────────────────────────────────────
# SDK — train_async
# ─────────────────────────────────────────────────────────────────────────────

class TestSDKAsyncTraining:

    def test_train_async_returns_task_id(self, sdk):
        task = sdk.train_async(model="SVM", dataset="circles", n_samples=100)
        assert task["id"]
        assert task["status"] in (STATE_PENDING, STATE_RUNNING)
        assert task["meta"]["model"] == "SVM"
        assert task["meta"]["dataset"] == "circles"

    def test_train_async_completes_and_registers_model(self, sdk):
        task = sdk.train_async(model="SVM", dataset="circles", n_samples=100)
        final = sdk.wait_for_task(task["id"], timeout=60)

        assert final["status"] == STATE_SUCCEEDED, final.get("error")
        result = final["result"]
        assert 0.0 <= result["accuracy"] <= 1.0
        assert result["model_id"], "Async training must register the model"
        assert result["model_type"] == "SVM"

    def test_registered_model_is_loadable(self, sdk):
        task = sdk.train_async(model="LR", dataset="moons", n_samples=100)
        final = sdk.wait_for_task(task["id"], timeout=60)
        model_id = final["result"]["model_id"]

        loaded = sdk.load_model(model_id)
        preds = sdk.predict(model_id, X=[[0.0, 0.0], [1.0, 1.0]])
        assert len(preds) == 2

    def test_async_and_sync_produce_same_accuracy(self, sdk):
        """Async must not drift from sync — same code path, same seed."""
        sync_result = sdk.train(model="SVM", dataset="circles", n_samples=200)

        task = sdk.train_async(model="SVM", dataset="circles", n_samples=200)
        final = sdk.wait_for_task(task["id"], timeout=60)

        assert final["status"] == STATE_SUCCEEDED
        assert abs(final["result"]["accuracy"] - sync_result.accuracy) < 1e-9

    def test_get_task_returns_current_state(self, sdk):
        task = sdk.train_async(model="NB", dataset="blobs", n_samples=100)
        sdk.wait_for_task(task["id"], timeout=60)
        fetched = sdk.get_task(task["id"])
        assert fetched["id"] == task["id"]
        assert fetched["status"] == STATE_SUCCEEDED

    def test_get_task_unknown_raises_sdk_error(self, sdk):
        from ml_db.errors import TaskNotFoundError as SDKTaskNotFoundError
        with pytest.raises(SDKTaskNotFoundError):
            sdk.get_task("2026-01-01_nope")

    def test_list_tasks_includes_async_task(self, sdk):
        task = sdk.train_async(model="NB", dataset="blobs", n_samples=100)
        sdk.wait_for_task(task["id"], timeout=60)
        tasks = sdk.list_tasks()
        assert any(t["id"] == task["id"] for t in tasks)

    def test_list_tasks_filter_by_status(self, sdk):
        task = sdk.train_async(model="NB", dataset="blobs", n_samples=100)
        sdk.wait_for_task(task["id"], timeout=60)
        succeeded = sdk.list_tasks(status=STATE_SUCCEEDED)
        assert len(succeeded) == 1
        assert succeeded[0]["id"] == task["id"]

    def test_train_async_validates_dataset_eagerly(self, sdk):
        """Bad input must raise immediately, not fail inside the worker."""
        from ml_db.errors import UnknownDatasetError
        with pytest.raises(UnknownDatasetError):
            sdk.train_async(dataset="does_not_exist")

    def test_train_async_validates_model_eagerly(self, sdk):
        from ml_db.errors import UnknownModelError
        with pytest.raises(UnknownModelError):
            sdk.train_async(model="NO_SUCH_MODEL")

    def test_train_async_validates_test_size(self, sdk):
        from ml_db.errors import InvalidInputError
        with pytest.raises(InvalidInputError):
            sdk.train_async(test_size=1.5)

    def test_task_state_survives_client_restart(self, sdk, tmp_path):
        """A new client over the same tasks dir sees the finished task."""
        task = sdk.train_async(model="NB", dataset="blobs", n_samples=100)
        sdk.wait_for_task(task["id"], timeout=60)

        from ml_db import MLDB
        fresh = MLDB(
            registry_base=tmp_path / "registry",
            tasks_dir=tmp_path / "registry" / "tasks",
        )
        restored = fresh.get_task(task["id"])
        assert restored["status"] == STATE_SUCCEEDED
        assert restored["result"]["model_id"]

    def test_task_tags_are_applied(self, sdk):
        task = sdk.train_async(
            model="NB", dataset="blobs", n_samples=100, tags=["nightly", "v12"]
        )
        final = sdk.wait_for_task(task["id"], timeout=60)
        model_id = final["result"]["model_id"]
        assert set(sdk.list_tags()) >= {"nightly", "v12"}
        assert len(sdk.list_models_by_tag("nightly")) == 1


# ─────────────────────────────────────────────────────────────────────────────
# API contracts
# ─────────────────────────────────────────────────────────────────────────────

class FakeReq:
    """Fake Vercel req object."""

    def __init__(self, body=None, args=None):
        self._body = body if body is not None else {}
        self.args = args or {}

    def get_json(self):
        return self._body


class FakeRes:
    """Fake Vercel res object."""

    def __init__(self):
        self.status = None
        self.data = None

    def json(self, d):
        self.data = d


class TestAsyncAPIContract:

    def test_train_async_returns_202_and_task_id(self, monkeypatch, tmp_path):
        """POST /api/train_async → 202 with a pollable task id."""
        from api import train_async
        from ml_db.client import MLDB

        monkeypatch.setattr(
            train_async, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        fr = FakeRes()
        train_async.handle(FakeReq({"model": "SVM", "dataset": "circles"}), fr)

        assert fr.status == 202, f"Expected 202, got {fr.status}"
        assert fr.data["id"]
        assert fr.data["status"] in (STATE_PENDING, STATE_RUNNING)

    def test_train_async_unknown_dataset_returns_400(self, monkeypatch, tmp_path):
        from api import train_async
        from ml_db.client import MLDB

        monkeypatch.setattr(
            train_async, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        fr = FakeRes()
        train_async.handle(FakeReq({"dataset": "nope"}), fr)
        assert fr.status == 400
        assert "nope" in fr.data["error"]
        assert fr.data["code"] == "E2001_UNKNOWN_DATASET"

    def test_train_async_unknown_model_returns_400(self, monkeypatch, tmp_path):
        from api import train_async
        from ml_db.client import MLDB

        monkeypatch.setattr(
            train_async, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        fr = FakeRes()
        train_async.handle(FakeReq({"model": "NOPE"}), fr)
        assert fr.status == 400
        assert fr.data["code"] == "E2002_UNKNOWN_MODEL"

    def test_tasks_endpoint_lists_tasks(self, monkeypatch, tmp_path):
        from api import tasks
        from ml_db.client import MLDB

        monkeypatch.setattr(
            tasks, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        fr = FakeRes()
        tasks.handle(FakeReq(args={}), fr)
        assert fr.status is None
        assert fr.data["count"] == 0
        assert fr.data["tasks"] == []

    def test_tasks_endpoint_returns_single_task(self, monkeypatch, tmp_path):
        from api import tasks
        from ml_db.client import MLDB

        monkeypatch.setattr(
            tasks, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        db = MLDB(
            registry_base=tmp_path / "registry",
            tasks_dir=tmp_path / "registry" / "tasks",
        )
        task = db.train_async(model="NB", dataset="blobs", n_samples=100)
        db.wait_for_task(task["id"], timeout=60)

        fr = FakeRes()
        tasks.handle(FakeReq(args={"id": task["id"]}), fr)
        assert fr.status is None
        assert fr.data["id"] == task["id"]
        assert fr.data["status"] == STATE_SUCCEEDED

    def test_tasks_endpoint_unknown_id_returns_404(self, monkeypatch, tmp_path):
        from api import tasks
        from ml_db.client import MLDB

        monkeypatch.setattr(
            tasks, "MLDB",
            lambda *a, **k: MLDB(
                registry_base=tmp_path / "registry",
                tasks_dir=tmp_path / "registry" / "tasks",
            ),
        )

        fr = FakeRes()
        tasks.handle(FakeReq(args={"id": "2026-01-01_ghost"}), fr)
        assert fr.status == 404
        assert fr.data["code"] == "E2005_TASK_NOT_FOUND"
