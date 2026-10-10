"""Tests for core.experiment_history module. v11 DoD #3."""

import json
import tempfile
from pathlib import Path

import pytest

from core.experiment_history import (
    clear_history,
    get_history,
    log_experiment,
)


@pytest.fixture
def tmp_exp_file(monkeypatch):
    """Redirect the JSONL path to a temp file for isolated testing."""
    import core.experiment_history as eh

    tmp = Path(tempfile.gettempdir()) / "test_ml_db_exp.jsonl"
    tmp.unlink(missing_ok=True)

    original = eh._experiments_file

    def _fake():
        return tmp

    monkeypatch.setattr(eh, "_experiments_file", _fake)
    yield tmp
    tmp.unlink(missing_ok=True)


class TestLogExperiment:
    def test_log_single_experiment(self, tmp_exp_file):
        clear_history()
        record_id = log_experiment(
            model="SVM",
            dataset="circles",
            accuracy=0.93,
            train_time=0.05,
            params={"C": 1.0},
            n_samples=500,
        )
        assert isinstance(record_id, str)
        assert len(record_id) == 8  # short uuid

        history = get_history(limit=10)
        assert len(history) == 1
        assert history[0]["model"] == "SVM"
        assert history[0]["dataset"] == "circles"
        assert history[0]["accuracy"] == 0.93
        assert "id" in history[0]
        assert "timestamp" in history[0]

    def test_log_multiple_experiments(self, tmp_exp_file):
        clear_history()
        id1 = log_experiment(model="SVM", dataset="circles", accuracy=0.93, train_time=0.05, params={}, n_samples=500)
        id2 = log_experiment(model="RF", dataset="moons", accuracy=0.91, train_time=0.12, params={}, n_samples=500)
        id3 = log_experiment(model="KNN", dataset="blobs", accuracy=0.88, train_time=0.01, params={}, n_samples=500)

        history = get_history(limit=10)
        assert len(history) == 3
        assert history[0]["id"] == id1
        assert history[1]["id"] == id2
        assert history[2]["id"] == id3

    def test_log_experiment_id_uniqueness(self, tmp_exp_file):
        clear_history()
        ids = [log_experiment(model="SVM", dataset="circles", accuracy=0.9, train_time=0.1, params={}, n_samples=500) for _ in range(10)]
        assert len(set(ids)) == 10  # all unique


class TestGetHistory:
    def test_get_history_empty(self, tmp_exp_file):
        clear_history()
        assert get_history(limit=10) == []

    def test_get_history_nonexistent_file(self, tmp_exp_file):
        tmp_exp_file.unlink(missing_ok=True)
        assert get_history(limit=10) == []

    def test_get_history_limit(self, tmp_exp_file):
        clear_history()
        for i in range(15):
            log_experiment(model="SVM", dataset="circles", accuracy=0.9, train_time=0.1, params={}, n_samples=500)
        history = get_history(limit=5)
        assert len(history) == 5

    def test_get_history_respects_limit_order(self, tmp_exp_file):
        clear_history()
        for i in range(10):
            log_experiment(model="SVM", dataset="circles", accuracy=i / 10, train_time=0.1, params={}, n_samples=500)
        history = get_history(limit=3)
        # Last 3 records
        assert len(history) == 3
        assert history[0]["accuracy"] == 0.7
        assert history[1]["accuracy"] == 0.8
        assert history[2]["accuracy"] == 0.9


class TestClearHistory:
    def test_clear_history(self, tmp_exp_file):
        log_experiment(model="SVM", dataset="circles", accuracy=0.93, train_time=0.05, params={}, n_samples=500)
        log_experiment(model="RF", dataset="moons", accuracy=0.91, train_time=0.12, params={}, n_samples=500)
        clear_history()
        assert get_history(limit=10) == []


class TestExperimentsJsonlFormat:
    def test_jsonl_one_line_per_record(self, tmp_exp_file):
        clear_history()
        log_experiment(model="SVM", dataset="circles", accuracy=0.93, train_time=0.05, params={}, n_samples=500)
        log_experiment(model="RF", dataset="moons", accuracy=0.91, train_time=0.12, params={}, n_samples=500)
        raw = tmp_exp_file.read_text()
        lines = [l for l in raw.splitlines() if l.strip()]
        assert len(lines) == 2
        # Each line is valid JSON
        for line in lines:
            rec = json.loads(line)
            assert "id" in rec
            assert "timestamp" in rec
            assert "model" in rec
            assert "accuracy" in rec
