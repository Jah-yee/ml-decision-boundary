"""Test benchmarks/__main__.py CLI entry point (python3 -m benchmarks)."""
import subprocess
import sys
import json
import tempfile
import os
from pathlib import Path

project_root = Path(__file__).parent.parent


def test_benchmarks_module_entrypoint_quick():
    """python3 -m benchmarks --quick runs successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--quick"],
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"


def test_benchmarks_module_full_suite():
    """python3 -m benchmarks runs full suite and produces JSON."""
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--report"],
        capture_output=True,
        text=True,
        timeout=300,
        cwd=project_root,
    )
    assert result.returncode == 0, f"stderr: {result.stderr}\nstdout: {result.stdout}"
    # Report is written to benchmarks/reports/YYYY-MM-DD.json
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    json_path = os.path.join(project_root, "benchmarks", "reports", f"{today}.json")
    assert os.path.exists(json_path), f"JSON report not created at {json_path}"
    with open(json_path) as f:
        data = json.load(f)
    assert "summary" in data
    assert "results" in data


def test_benchmarks_module_help():
    """python3 -m benchmarks --help shows usage."""
    result = subprocess.run(
        [sys.executable, "-m", "benchmarks", "--help"],
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0
    assert "benchmark" in result.stdout.lower() or "--quick" in result.stdout
