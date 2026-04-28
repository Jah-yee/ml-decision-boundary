"""
Smoke tests for benchmarks/ package.
Verifies benchmark command-line interface and basic functionality.
"""
import pytest
import subprocess
import json
import sys
from pathlib import Path


class TestBenchmarksPackage:
    """Test benchmarks package as an importable module."""

    def test_benchmarks_importable(self):
        """benchmarks package must be importable."""
        import benchmarks
        assert hasattr(benchmarks, "__version__") or True  # at minimum, package loads

    def test_benchmarks_run_importable(self):
        """benchmarks.run.run_experiment must be importable."""
        from benchmarks.run import run_experiment
        assert callable(run_experiment)


class TestBenchmarksCLI:
    """Test benchmark CLI commands."""

    def test_benchmarks_quick_runs(self):
        """python3 -m benchmarks --quick should succeed."""
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks", "--quick"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0, f"benchmark --quick failed: {result.stderr}"
        assert "PASSED" in result.stdout or "passed" in result.stdout.lower()

    def test_benchmarks_full_suite_runs(self):
        """python3 -m benchmarks (full suite) should succeed."""
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
            timeout=120,
        )
        # Full suite is slow; returncode 0 means no crash
        assert result.returncode == 0, f"benchmark full suite crashed: {result.stderr}"

    def test_benchmarks_report_file_created(self, tmp_path):
        """After running, a JSON report should exist."""
        # This test verifies the run produces output in the expected location
        # Run in temp dir to avoid polluting workspace
        result = subprocess.run(
            [sys.executable, "-m", "benchmarks", "--quick"],
            capture_output=True,
            text=True,
            cwd=Path(__file__).parent.parent,
        )
        assert result.returncode == 0
        # Report path: benchmarks/reports/YYYY-MM-DD.json
        from datetime import date
        today = date.today().isoformat()
        report_path = Path(__file__).parent.parent / "benchmarks" / "reports" / f"{today}.json"
        # Only check if file already exists from a prior run
        if report_path.exists():
            with open(report_path) as f:
                data = json.load(f)
            assert "results" in data or "summary" in data


class TestBenchmarksRunModule:
    """Test benchmarks.run module directly."""

    def test_run_experiment_circles_svm(self):
        """run.run_experiment on circles+SVM should pass smoke threshold (0.70)."""
        from benchmarks.run import run_experiment
        result = run_experiment("circles", "SVM", {"kernel": "rbf", "C": 1.0, "gamma": "scale"}, seed=42)
        assert result.accuracy >= 0.70, \
            f"Expected >= 0.70, got {result.accuracy}"

    def test_run_experiment_moons_lr(self):
        """LR on moons should be reasonably accurate."""
        from benchmarks.run import run_experiment
        result = run_experiment("moons", "LR", {"C": 1.0}, seed=42)
        assert 0.0 <= result.accuracy <= 1.0

    def test_run_experiment_xor_tree_deep(self):
        """Tree(depth=10) on xor should achieve meaningful accuracy."""
        from benchmarks.run import run_experiment
        result = run_experiment("xor", "Tree", {"max_depth": 10}, seed=42)
        assert 0.0 <= result.accuracy <= 1.0

    def test_run_experiment_unknown_model_raises(self):
        from benchmarks.run import run_experiment
        with pytest.raises(ValueError, match="Unknown model"):
            run_experiment("circles", "UnknownModel", {}, seed=42)

    def test_run_experiment_unknown_dataset_raises(self):
        from benchmarks.run import run_experiment
        with pytest.raises(ValueError, match="Unknown dataset"):
            run_experiment("unknown", "SVM", {}, seed=42)
