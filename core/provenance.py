"""Experiment provenance capture for v13 DoD #1, replay recipes for DoD #2.

DoD #1 records reproducibility-relevant run conditions: random seed, dataset
parameters, resolved hyperparameters, runtime versions, Git commit and a
stable SHA-256 fingerprint. No credentials or full environment dumps are
stored.

DoD #2 turns that record into an executable *replay recipe*:

  * :func:`build_replay_plan` derives a canonical SDK snippet (always exact)
    and a CLI command (only when every value survives the CLI's lossy
    ``--params`` parser — see :func:`cli_params_roundtrip_safe`).
  * :func:`dependency_digest` hashes the pinned dependency set so a replay
    can be checked against the environment that produced the original run.

The CLI command is deliberately conservative: if a hyperparameter value
cannot be represented faithfully by ``main.py --params`` (tuples, ``None``,
booleans-as-strings, ...) the command is marked ``cli_exact: false`` and the
SDK snippet is advertised as the authoritative replay path.
"""
from __future__ import annotations

import hashlib
import json
import platform
import shlex
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__all__ = [
    "build_provenance",
    "compute_fingerprint",
    "environment_info",
    "git_info",
    "canonical_json",
    "provenance_diff",
    "build_replay_command",
    "build_replay_plan",
    "dependency_digest",
    "cli_params_roundtrip_safe",
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


# ── v13 DoD #2: Reproducibility replay ───────────────────────────────────────


#: Model families the CLI can express via ``main.py --model``.
CLI_MODEL_CHOICES: Tuple[str, ...] = (
    "SVM", "LR", "Tree", "RF", "KNN", "MLP", "NB", "GB", "ET", "AB",
)

#: Hyperparameter names that the CLI passes *itself* to the estimator
#: (``main.train_model``), e.g. ``SVC(**params, random_state=42)``.
#: A recorded value for one of these keys makes the CLI raise
#: ``TypeError: got multiple values for keyword argument`` instead of
#: training, so such a run is never CLI-replayable.
CLI_HARDCODED_KWARGS: Dict[str, Tuple[str, ...]] = {
    "SVM": ("random_state",),
    "LR": ("random_state", "max_iter"),
    "Tree": ("random_state",),
    "RF": ("random_state",),
    "KNN": (),
    "MLP": ("random_state", "max_iter"),
    "NB": (),
    "GB": ("random_state",),
    "ET": ("random_state",),
    "AB": ("random_state", "algorithm"),
}

#: Model families whose CLI construction differs from the SDK's
#: (``core.train_utils.build_model``), so a CLI replay can never reproduce
#: an SDK-trained model of that family.  ``MLP`` differs in ``max_iter``
#: (CLI 2000 vs SDK 500).
CLI_DIVERGENT_FAMILIES: Tuple[str, ...] = ("MLP",)

#: Dataset constants the CLI training path actually uses
#: (``main.run_experiment`` hardcodes these; the ``--n-samples`` / ``--noise``
#: flags only affect the *plot*, not the trained model).
CLI_TRAIN_N_SAMPLES = 500
CLI_TRAIN_NOISE = 0.3
CLI_TRAIN_TEST_SIZE = 0.2

#: Parameter values the CLI's ``parse_params`` cannot round-trip faithfully.
#:
#: ``main.parse_params`` coerces to int/float/bool and otherwise keeps the
#: raw string.  A value such as ``(50,)`` therefore arrives at sklearn as the
#: *string* ``"(50,)"``, silently producing a different model than the one
#: that was recorded.  We detect that class of value and refuse to emit a
#: CLI command that claims to be exact.
_CLI_LOSSY_TYPES = (tuple, list, set, dict, type(None))


def _repo_root() -> Path:
    """Return the repository root (the parent of the ``core`` package)."""
    return Path(__file__).resolve().parents[1]


def dependency_digest(repo_root: Optional[Path] = None) -> Dict[str, Any]:
    """Hash the pinned dependency set used to build the project.

    The digest covers ``requirements.lock`` — the file that pins every
    transitive dependency — so two environments can be compared before
    attempting a replay.

    Args:
        repo_root: repository root. Defaults to the package's own root.

    Returns:
        A dict with ``digest`` (``sha256:<16hex>`` or ``"unknown"``),
        ``source`` (relative path or ``"unknown"``), ``package_count`` and
        ``available`` (bool).  Never raises: a missing lock file degrades
        to ``digest: "unknown"`` rather than failing a training run.
    """
    root = Path(repo_root) if repo_root else _repo_root()
    lock_path = root / "requirements.lock"
    try:
        raw = lock_path.read_bytes()
    except Exception:
        return {
            "digest": "unknown",
            "source": "unknown",
            "package_count": 0,
            "available": False,
        }

    digest = hashlib.sha256(raw).hexdigest()
    text = raw.decode("utf-8", errors="replace")
    package_count = sum(
        1 for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#") and "==" in line
    )
    try:
        source = str(lock_path.relative_to(root))
    except Exception:
        source = str(lock_path)
    return {
        "digest": "sha256:" + digest[:16],
        "source": source,
        "package_count": package_count,
        "available": True,
    }


def cli_params_roundtrip_safe(params: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Check whether hyperparameter values survive the CLI ``--params`` parser.

    The CLI parses ``KEY=VALUE`` pairs and coerces them to ``int``, ``float``
    or ``bool``; everything else stays a string.  A value is only faithful
    when it round-trips with the *same type and the same value*:

    * tuples / lists / sets / dicts / ``None`` lose their type (``(50,)``
      becomes the string ``"(50,)"``);
    * numeric **strings** are silently retyped (``"1"`` becomes ``int`` 1),
      which changes both the model and its fingerprint;
    * ``bool`` survives, but only because ``parse_params`` maps the
      literals ``"true"`` / ``"false"`` back to a bool.

    Args:
        params: the resolved hyperparameters.

    Returns:
        ``(safe, unsafe_keys)`` where ``safe`` is True only when every value
        round-trips exactly and ``unsafe_keys`` lists the offending keys.
    """
    unsafe: List[str] = []
    for key, value in sorted((params or {}).items()):
        if isinstance(value, _CLI_LOSSY_TYPES):
            unsafe.append(key)
            continue
        if isinstance(value, bool):
            # ``parse_params`` maps "true"/"false" to a bool — this one is fine.
            continue
        if isinstance(value, (int, float)):
            continue
        if isinstance(value, str):
            # A bare string is preserved verbatim *unless* it happens to look
            # numeric or boolean — then the parser retypes it.
            if _parse_params_value(value) != value:
                unsafe.append(key)
            continue
        unsafe.append(key)
    return (not unsafe, unsafe)


def _parse_params_value(value: str) -> Any:
    """Replicate ``main.parse_params`` coercion for a single raw string.

    Kept in sync with ``main.parse_params``; ``tests/test_replay.py``
    locks the two together so a future change to the CLI parser cannot
    silently invalidate the replay-honesty rules.
    """
    try:
        return int(value)
    except (TypeError, ValueError):
        pass
    try:
        return float(value)
    except (TypeError, ValueError):
        pass
    lowered = str(value).lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return value


def _format_cli_value(value: Any) -> str:
    """Render one hyperparameter value as a CLI ``KEY=VALUE`` token."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return repr(value)
    return str(value)


def build_replay_command(record: Dict[str, Any]) -> Dict[str, Any]:
    """Build a copy-pasteable CLI command that reproduces a recorded run.

    The command is only marked ``exact: True`` when the CLI would really
    reproduce the recorded run.  That is a deliberately strict bar, because
    the CLI's training path differs from the SDK's in several ways:

    * ``main.run_experiment`` hardcodes ``n_samples=500``, ``noise=0.3`` and
      ``test_size=0.2``.  The ``--n-samples`` / ``--noise`` flags only feed
      the *plot*, not the trained model — so they are never emitted (they
      would be a lie) and a recorded run with other values is not exact.
    * The CLI passes ``random_state`` / ``max_iter`` / ``algorithm`` itself,
      so a recorded value for one of those keys makes the CLI crash with
      ``TypeError: got multiple values for keyword argument``.
    * ``MLP`` is built with ``max_iter=2000`` by the CLI but ``max_iter=500``
      by the SDK, so a CLI replay of an SDK-trained MLP is a different model.
    * ``test_size`` and the recorded ``seed`` are not always CLI-expressible.

    Anything the CLI cannot express faithfully is reported in ``warnings``,
    and the caller is expected to fall back to the (always exact) SDK recipe.

    Args:
        record: a provenance record as produced by :func:`build_provenance`.

    Returns:
        A dict with ``command`` (the CLI string), ``exact`` (bool),
        ``warnings`` (list of str) and ``params`` (the CLI token list).
    """
    record = record or {}
    dataset = record.get("dataset") or {}
    params = record.get("hyperparameters") or {}
    model_type = record.get("model_type") or ""
    warnings: List[str] = []

    tokens: List[str] = ["python", "main.py"]
    if model_type:
        if model_type in CLI_MODEL_CHOICES:
            tokens += ["--model", model_type]
        else:
            warnings.append(
                f"model_type '{model_type}' is not accepted by the CLI "
                f"(choices: {', '.join(CLI_MODEL_CHOICES)}); use the SDK recipe."
            )

    dataset_name = dataset.get("name")
    if dataset_name and dataset_name != "unknown":
        tokens += ["--dataset", str(dataset_name)]

    # The CLI's training path hardcodes the dataset shape (see
    # CLI_TRAIN_N_SAMPLES / CLI_TRAIN_NOISE).  The --n-samples / --noise
    # flags affect the visualisation only, so emitting them would suggest a
    # fidelity the CLI does not have.  They are omitted on purpose.
    n_samples = dataset.get("n_samples")
    if n_samples is not None and int(n_samples) != CLI_TRAIN_N_SAMPLES:
        warnings.append(
            f"n_samples={n_samples!r} is not used by the CLI training path "
            f"(it always trains on {CLI_TRAIN_N_SAMPLES} samples); "
            "use the SDK recipe for an exact replay."
        )
    noise = dataset.get("noise")
    if noise is not None and float(noise) != CLI_TRAIN_NOISE:
        warnings.append(
            f"noise={noise!r} is not used by the CLI training path "
            f"(it always uses {CLI_TRAIN_NOISE}); "
            "use the SDK recipe for an exact replay."
        )

    seed = record.get("seed")
    if seed is not None:
        tokens += ["--seed", str(seed)]
    else:
        warnings.append(
            "no seed was recorded for this run, so the CLI command cannot "
            "guarantee the same split; use the SDK recipe."
        )

    safe, unsafe = cli_params_roundtrip_safe(params)
    if unsafe:
        warnings.append(
            "hyperparameters " + ", ".join(repr(k) for k in unsafe)
            + " cannot be represented by the CLI --params parser; "
            "use the SDK recipe for an exact replay."
        )

    # Keys the CLI passes to the estimator itself would make it crash.
    hardcoded = CLI_HARDCODED_KWARGS.get(model_type, ())
    colliding = [k for k in params if k in hardcoded]
    if colliding:
        warnings.append(
            "hyperparameters " + ", ".join(repr(k) for k in sorted(colliding))
            + f" are set by the CLI itself for {model_type} and would make it "
            "fail with 'multiple values for keyword argument'; "
            "use the SDK recipe for an exact replay."
        )

    # Families whose CLI construction differs from the SDK's.
    if model_type in CLI_DIVERGENT_FAMILIES:
        warnings.append(
            f"the CLI builds {model_type} differently from the SDK "
            "(different solver defaults), so a CLI replay is not equivalent; "
            "use the SDK recipe for an exact replay."
        )

    for key in sorted(params):
        tokens += ["--params", f"{key}={_format_cli_value(params[key])}"]

    test_size = dataset.get("test_size")
    if test_size is not None and float(test_size) != CLI_TRAIN_TEST_SIZE:
        warnings.append(
            f"test_size={test_size!r} is not exposed by the CLI; "
            "use the SDK recipe for an exact replay."
        )

    exact = safe and not warnings
    return {
        "command": " ".join(shlex.quote(tok) for tok in tokens),
        "tokens": tokens,
        "exact": exact,
        "warnings": warnings,
        "params": [f"{k}={_format_cli_value(params[k])}" for k in sorted(params)],
    }


def _sdk_replay_snippet(record: Dict[str, Any]) -> str:
    """Render the canonical, exact SDK replay snippet for a run."""
    dataset = record.get("dataset") or {}
    params = record.get("hyperparameters") or {}
    model_type = record.get("model_type") or "unknown"
    seed = record.get("seed")

    def _lit(value: Any) -> str:
        return repr(value)

    dataset_kwargs = [
        f"name={_lit(dataset.get('name', 'unknown'))}",
    ]
    if dataset.get("n_samples") is not None:
        dataset_kwargs.append(f"n_samples={_lit(dataset.get('n_samples'))}")
    if dataset.get("noise") is not None:
        dataset_kwargs.append(f"noise={_lit(dataset.get('noise'))}")
    if dataset.get("test_size") is not None:
        dataset_kwargs.append(f"test_size={_lit(dataset.get('test_size'))}")

    lines = [
        "from ml_db import MLDB",
        "",
    ]
    if seed is not None:
        lines.append("db = MLDB(seed=%s)" % _lit(seed))
    else:
        # No seed was recorded — fall back to the SDK default but say so, so
        # the snippet is not mistaken for a faithful replay of the original.
        lines.append("db = MLDB()  # NOTE: no seed was recorded for this run")
    lines += [
        "result = db.train(",
        "    model=%s," % _lit(model_type),
        "    dataset=%s," % _lit(dataset.get("name", "unknown")),
        "    n_samples=%s," % _lit(dataset.get("n_samples", 500)),
        "    noise=%s," % _lit(dataset.get("noise", 0.3)),
        "    test_size=%s," % _lit(dataset.get("test_size", 0.2)),
        "    params=%s," % _lit(dict(params)),
        ")",
        "print(result.model_id, result.accuracy)",
    ]
    # `dataset_kwargs` is retained for callers that want the raw field list.
    del dataset_kwargs
    return "\n".join(lines)


def build_replay_plan(
    record: Dict[str, Any],
    repo_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """Build a complete, executable replay recipe from a provenance record.

    The plan contains:

    * ``sdk`` — an exact Python snippet that re-runs the experiment with
      identical seed / dataset parameters / hyperparameters.
    * ``cli`` — a CLI command, flagged ``exact`` only when it faithfully
      reproduces the run.
    * ``dependencies`` — the digest of the pinned dependency set.
    * ``expected`` — the original fingerprint, so a replay can be verified.

    Args:
        record: a provenance record.
        repo_root: repository root used to locate ``requirements.lock``.

    Returns:
        A JSON-serializable dict.
    """
    record = record or {}
    dataset = record.get("dataset") or {}
    cli = build_replay_command(record)
    dependencies = dependency_digest(repo_root)
    fingerprint = record.get("fingerprint")
    if fingerprint is None and record:
        fingerprint = compute_fingerprint(record)

    return {
        "sdk": _sdk_replay_snippet(record),
        "cli": cli,
        "dependencies": dependencies,
        "expected": {
            "fingerprint": fingerprint,
            "accuracy": None,
            "seed": record.get("seed"),
            "model_type": record.get("model_type"),
            "dataset": {
                "name": dataset.get("name"),
                "n_samples": dataset.get("n_samples"),
                "noise": dataset.get("noise"),
                "test_size": dataset.get("test_size"),
            },
            "hyperparameters": dict(record.get("hyperparameters") or {}),
            "git_commit": (record.get("git") or {}).get("commit"),
        },
        "replayable": True,  # the SDK path always exists.
    }
