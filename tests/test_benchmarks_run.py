"""Tests for benchmarks/run.py"""

import pytest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
import json

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from benchmarks.run import (
    run_quick_benchmark,
    run_full_benchmark,
    generate_summary,
    write_report,
    MODELS,
    DATASETS,
    ACCURACY_THRESHOLDS,
)


class MockResult:
    def __init__(self, accuracy=0.85, train_time=0.1):
        self.accuracy = accuracy
        self.train_time = train_time


class TestRunQuickBenchmark:
    def test_run_quick_benchmark_smoke(self):
        result = run_quick_benchmark()
        assert result["smoke_test"] is True
        assert result["dataset"] == "circles"
        assert result["model"] == "SVM"
        assert "accuracy" in result
        assert "train_time" in result
        assert "wall_time" in result
        assert "passed" in result
        assert isinstance(result["passed"], bool)

    def test_run_quick_benchmark_passes_threshold(self):
        result = run_quick_benchmark()
        # circles threshold is 0.70; SVM rbf C=1 should pass
        assert result["accuracy"] >= ACCURACY_THRESHOLDS["circles"]


class TestGenerateSummary:
    def test_generate_summary_smoke_test(self):
        results = [
            {"dataset": "circles", "model": "SVM", "accuracy": 0.85,
             "train_time": 0.1, "wall_time": 0.2, "passed": True},
        ]
        summary = generate_summary(results, smoke_test=True)
        assert summary["smoke_test"] is True
        assert summary["accuracy"] == 0.85
        assert summary["passed"] is True
        assert summary["threshold"] == ACCURACY_THRESHOLDS["circles"]

    def test_generate_summary_full_suite(self):
        results = [
            {"dataset": "circles", "model": "SVM", "accuracy": 0.85,
             "train_time": 0.1, "passed": True},
            {"dataset": "circles", "model": "LR", "accuracy": 0.75,
             "train_time": 0.05, "passed": True},
            {"dataset": "moons", "model": "SVM", "accuracy": 0.65,
             "train_time": 0.1, "passed": False},
            {"dataset": "blobs", "model": "Tree", "accuracy": 0.95,
             "train_time": 0.03, "error": "some error", "passed": False},
        ]
        summary = generate_summary(results, smoke_test=False)
        assert summary["smoke_test"] is False
        assert summary["total_experiments"] == 4
        assert summary["passed"] == 2
        assert summary["failed"] == 2
        assert summary["errors"] == 1
        assert summary["best_accuracy"] == 0.95
        assert summary["worst_accuracy"] == 0.65
        assert abs(summary["avg_accuracy"] - 0.8) < 0.001
        assert "by_dataset" in summary

    def test_generate_summary_empty(self):
        summary = generate_summary([], smoke_test=False)
        assert summary["total_experiments"] == 0
        assert summary["best_accuracy"] is None
        assert summary["avg_accuracy"] is None


class TestWriteReport:
    def test_write_report_creates_files(self, tmp_path):
        results = [
            {"dataset": "circles", "model": "SVM", "accuracy": 0.85,
             "train_time": 0.1, "passed": True},
        ]
        summary = {"total_experiments": 1, "passed": 1, "failed": 0, "errors": 0,
                   "best_accuracy": 0.85, "worst_accuracy": 0.85, "avg_accuracy": 0.85,
                   "avg_train_time": 0.1}
        json_str, md_str = write_report(tmp_path, results, summary)
        json_path = Path(json_str)
        md_path = Path(md_str)
        assert json_path.exists()
        assert md_path.exists()
        data = json.loads(json_path.read_text())
        assert data["summary"]["total_experiments"] == 1

    def test_write_report_creates_md_with_summary(self, tmp_path):
        results = [
            {"dataset": "circles", "model": "SVM", "accuracy": 0.85,
             "train_time": 0.1, "passed": True},
        ]
        summary = {"total_experiments": 1, "passed": 1, "failed": 0, "errors": 0,
                   "avg_accuracy": 0.85, "avg_train_time": 0.1,
                   "best_accuracy": 0.85, "worst_accuracy": 0.85}
        json_str, md_str = write_report(tmp_path, results, summary)
        md_path = Path(md_str)
        content = md_path.read_text()
        assert "circles" in content
        assert "SVM" in content
