"""Experiment history logging for ml-decision-boundary.

Records each experiment run to `output/experiments.jsonl` (append-only JSONL).
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Path helpers
# ---------------------------------------------------------------------------

def _experiments_file() -> Path:
    """Return the path to the experiments JSONL file."""
    # resolve relative to this module's directory, then walk up to project root
    return Path(__file__).resolve().parent.parent / "output" / "experiments.jsonl"


def _ensure_output_dir() -> None:
    """Create the output directory if it does not already exist."""
    _experiments_file().parent.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def log_experiment(**kwargs: Any) -> str:
    """Append an experiment record to ``output/experiments.jsonl``.

    The supplied keyword arguments are enriched with ``id`` and ``timestamp``,
    then written as a single JSON line.

    Args:
        **kwargs: Experiment fields. At minimum should contain ``model``,
                  ``dataset``, ``accuracy``, ``train_time``, ``params``,
                  ``n_samples``.

    Returns:
        The generated short uuid for this experiment.

    Example:
        >>> record_id = log_experiment(
        ...     model="LogisticRegression",
        ...     dataset="mnist",
        ...     accuracy=0.91,
        ...     train_time=12.3,
        ...     params={"C": 1.0},
        ...     n_samples=60000,
        ... )
    """
    _ensure_output_dir()

    short_id = uuid.uuid4().hex[:8]
    timestamp = datetime.now(timezone.utc).isoformat()

    record: Dict[str, Any] = {
        "id": short_id,
        "timestamp": timestamp,
        **kwargs,
    }

    file_path = _experiments_file()
    with file_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")

    return short_id


def get_history(limit: int = 50) -> List[Dict[str, Any]]:
    """Read the last N experiment records from the JSONL file.

    Args:
        limit: Maximum number of records to return (default 50).
               Returns the newest ``limit`` entries.

    Returns:
        A list of experiment record dictionaries, newest entries last.
        Returns an empty list if the file does not exist.
    """
    file_path = _experiments_file()
    if not file_path.exists():
        return []

    # Read all lines and keep the last `limit` non-empty ones
    with file_path.open("r", encoding="utf-8") as fh:
        lines = [line.rstrip("\n") for line in fh if line.strip()]

    records: List[Dict[str, Any]] = []
    for line in lines[-limit:]:
        try:
            records.append(json.loads(line))
        except json.JSONDecodeError:
            # Skip malformed lines
            continue

    return records


def clear_history() -> None:
    """Truncate the experiments JSONL file.

    This is intended for testing use only.
    """
    file_path = _experiments_file()
    if file_path.exists():
        file_path.write_text("", encoding="utf-8")


# ---------------------------------------------------------------------------
# Smoke test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Basic sanity checks – safe to run directly
    import tempfile

    _original_file = _experiments_file

    def _fake_file() -> Path:
        return Path(tempfile.gettempdir()) / "test_experiments.jsonl"

    # Patch the file path helper so we don't touch the real output dir
    import core.experiment_history as eh  # type: ignore[attr-defined]
    eh._experiments_file = _fake_file  # type: ignore[attr-defined]

    try:
        eh.clear_history()

        # Log a few records
        id1 = eh.log_experiment(
            model="LogisticRegression",
            dataset="mnist",
            accuracy=0.91,
            train_time=12.3,
            params={"C": 1.0},
            n_samples=60000,
        )
        id2 = eh.log_experiment(
            model="SVC",
            dataset="mnist",
            accuracy=0.93,
            train_time=45.0,
            params={"C": 0.5, "kernel": "rbf"},
            n_samples=60000,
        )

        # Retrieve and verify
        history = eh.get_history(limit=10)
        assert len(history) == 2, f"Expected 2 records, got {len(history)}"
        assert history[0]["id"] == id1
        assert history[1]["id"] == id2
        assert history[0]["accuracy"] == 0.91
        assert history[1]["model"] == "SVC"

        # Test limit
        id3 = eh.log_experiment(
            model="KNN",
            dataset="iris",
            accuracy=0.97,
            train_time=1.2,
            params={"n_neighbors": 5},
            n_samples=150,
        )
        recent = eh.get_history(limit=2)
        assert len(recent) == 2
        assert recent[-1]["id"] == id3

        # Clear and verify
        eh.clear_history()
        assert eh.get_history() == []

        print("Smoke test PASSED")
    finally:
        eh._experiments_file = _original_file  # type: ignore[attr-defined]
        eh.clear_history()
