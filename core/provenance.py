"""Experiment provenance capture for v13 DoD #1.

Records reproducibility-relevant run conditions: random seed, dataset
parameters, resolved hyperparameters, runtime versions, Git commit and a
stable SHA-256 fingerprint. No credentials or full environment dumps are
stored.
"""
from __future__ import annotations

import hashlib
import json
import platform
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

__all__ = [
    "build_provenance",
    "compute_fingerprint",
    "environment_info",
    "git_info",
    "canonical_json",
    "provenance_diff",
]


def canonical_json(payload: Dict[str, Any]) -> str:
    """Return a stable JSON rendering with sorted keys and compact separators."""
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)


def _package_version(module_name: str) -> str:
    try:
        module = __import__(module_name)
    except Exception:
        return "unknown"
    version = getattr(module, "__version__", None)
    if not version:
        try:
            from importlib.metadata import version as _v
            version = _v(module_name)
        except Exception:
            version = "unknown"
    return str(version)


def environment_info() -> Dict[str, str]:
    """Describe Python and core numerical-library versions."""
    return {
        "python": platform.python_version(),
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "numpy": _package_version("numpy"),
        "scikit_learn": _package_version("sklearn"),
        "joblib": _package_version("joblib"),
    }


def git_info(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Describe the git checkout without raising."""
    root = Path(repo_root) if repo_root else Path(__file__).resolve().parents[1]

    def _run(*args: str) -> Optional[str]:
        try:
            out = subprocess.run(
                ["git", *args], cwd=str(root), capture_output=True,
                text=True, timeout=5,
            )
        except Exception:
            return None
        if out.returncode != 0:
            return None
        return (out.stdout or "").strip() or None

    dirty_raw = _run("status", "--porcelain")
    return {
        "commit": _run("rev-parse", "--short", "HEAD") or "unknown",
        "branch": _run("rev-parse", "--abbrev-ref", "HEAD") or "unknown",
        "dirty": bool(dirty_raw) if dirty_raw is not None else False,
    }


def compute_fingerprint(record: Dict[str, Any]) -> str:
    """Compute a stable fingerprint over reproducibility-relevant fields."""
    environment = record.get("environment") or {}
    relevant = {
        "seed": record.get("seed"),
        "dataset": record.get("dataset"),
        "hyperparameters": record.get("hyperparameters"),
        "environment": {
            "python": environment.get("python"),
            "numpy": environment.get("numpy"),
            "scikit_learn": environment.get("scikit_learn"),
            "joblib": environment.get("joblib"),
        },
        "git_commit": (record.get("git") or {}).get("commit"),
    }
    digest = hashlib.sha256(canonical_json(relevant).encode("utf-8")).hexdigest()
    return "sha256:" + digest[:16]


def build_provenance(
    seed: Optional[int] = None,
    dataset_name: str = "unknown",
    n_samples: int = 0,
    noise: float = 0.3,
    test_size: float = 0.2,
    hyperparameters: Optional[Dict[str, Any]] = None,
    model_type: str = "unknown",
    repo_root: Optional[Path] = None,
    include_environment: bool = True,
    include_git: bool = True,
) -> Dict[str, Any]:
    """Build a JSON-serializable provenance record for one training run."""
    record: Dict[str, Any] = {
        "seed": seed,
        "dataset": {
            "name": dataset_name,
            "n_samples": n_samples,
            "noise": noise,
            "test_size": test_size,
        },
        "hyperparameters": dict(hyperparameters or {}),
        "model_type": model_type,
        "environment": environment_info() if include_environment else {},
        "git": git_info(repo_root) if include_git else {
            "commit": "unknown", "branch": "unknown", "dirty": False,
        },
        "captured_at": datetime.now(timezone.utc).isoformat(),
    }
    record["fingerprint"] = compute_fingerprint(record)
    return record


def provenance_diff(
    left: Optional[Dict[str, Any]],
    right: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    """Compare two provenance records field by field.

    ``captured_at`` and ``git.dirty`` are excluded because they describe
    capture context rather than run reproducibility conditions.
    """
    left = left or {}
    right = right or {}
    fields = [
        ("seed", left.get("seed"), right.get("seed")),
        ("model_type", left.get("model_type"), right.get("model_type")),
        ("dataset", left.get("dataset") or {}, right.get("dataset") or {}),
        ("hyperparameters", left.get("hyperparameters") or {}, right.get("hyperparameters") or {}),
        ("environment", left.get("environment") or {}, right.get("environment") or {}),
        ("git.commit", (left.get("git") or {}).get("commit"), (right.get("git") or {}).get("commit")),
    ]
    differences = [
        {"field": name, "left": lval, "right": rval}
        for name, lval, rval in fields if lval != rval
    ]
    left_fp = left.get("fingerprint")
    right_fp = right.get("fingerprint")
    if left_fp is None and left:
        left_fp = compute_fingerprint(left)
    if right_fp is None and right:
        right_fp = compute_fingerprint(right)
    return {
        "identical": not differences,
        "fingerprint_match": bool(left_fp) and left_fp == right_fp,
        "left_fingerprint": left_fp,
        "right_fingerprint": right_fp,
        "differences": differences,
    }
