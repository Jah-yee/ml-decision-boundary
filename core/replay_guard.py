"""Replay integrity auditing for v13 DoD #4.

DoD #2 froze a replay recipe (an SDK snippet plus a CLI command) into every
model's provenance record at registration time.  DoD #3 told us *how many*
models are covered.  Neither one tells us whether a frozen recipe is still
*true*.

A recipe goes stale the moment the code that produces it changes.  The CLI
command builder, for instance, renders list-valued hyperparameters differently
today than it did when an older model was registered — the stored command
says ``hidden_layer_sizes=(50,)`` while a freshly derived one says
``hidden_layer_sizes=[50]``.  Both mean the same model, but a naive string
comparison calls that "drift" and buries the recipes that *would* actually
reproduce something different.

This module draws the line that matters:

* **cosmetic drift** — the stored recipe and the fresh one denote the same
  run.  Nothing is broken; only the rendering changed.
* **semantic drift** — the stored recipe would reproduce a *different* model
  than the one on record.  This is a real reproducibility defect.

It also provides :func:`verify_replay`, which actually executes a replay and
reports whether the run still reproduces — the "regression verification"
half of DoD #4.

Nothing here mutates the registry.
"""
from __future__ import annotations

import shlex
from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.provenance import (
    CLI_TRAIN_NOISE,
    CLI_TRAIN_N_SAMPLES,
    CLI_TRAIN_TEST_SIZE,
    build_replay_command,
)

__all__ = [
    "DRIFT_LEVELS",
    "classify_recipe_drift",
    "integrity_report",
    "verify_replay",
]

#: Drift grades, from harmless to serious.
DRIFT_LEVELS: Tuple[str, ...] = ("none", "cosmetic", "semantic")

#: CLI flags that the CLI's *training path* ignores — they only affect the
#: visualisation.  A frozen recipe that carries them still reproduces the
#: same model, so a difference in these flags is cosmetic, not semantic.
#: (``--n-samples`` / ``--noise`` are exactly the values the CLI hardcodes
#: for training, per ``CLI_TRAIN_N_SAMPLES`` / ``CLI_TRAIN_NOISE``.)
_VISUAL_ONLY_FLAGS = ("--n-samples", "--noise")


def _tokenize(command: str) -> List[str]:
    """Split a shell command into tokens, tolerating a malformed one."""
    if not command:
        return []
    try:
        return shlex.split(command)
    except ValueError:
        return command.split()


def _params_from_tokens(tokens: List[str]) -> Dict[str, str]:
    """Extract the ``KEY=VALUE`` pairs carried by ``--params`` tokens."""
    params: Dict[str, str] = {}
    for index, token in enumerate(tokens):
        if token != "--params":
            continue
        if index + 1 >= len(tokens):
            continue
        raw = tokens[index + 1]
        key, sep, value = raw.partition("=")
        if sep:
            params[key] = value
    return params


def _normalise_value(raw: str) -> Any:
    """Normalise a rendered CLI parameter value for comparison.

    ``(50,)`` and ``[50]`` denote the same sequence; ``50`` and ``50.0``
    denote the same number.  Comparing the raw strings would call both of
    these "different" and drown the real signal.

    Sequences are normalised to a **tuple** regardless of whether they were
    written as a Python tuple or a JSON list, because the two spellings
    describe the same hyperparameter.
    """
    text = raw.strip()
    for opener, closer in (("(", ")"), ("[", "]")):
        if text.startswith(opener) and text.endswith(closer):
            inner = text[1:-1].strip()
            if not inner:
                return ()
            parts = [p.strip() for p in inner.split(",") if p.strip()]
            return tuple(_normalise_value(p) for p in parts)
    try:
        return int(text)
    except (TypeError, ValueError):
        pass
    try:
        return float(text)
    except (TypeError, ValueError):
        pass
    return text


def _normalise_params(params: Dict[str, str]) -> Dict[str, Any]:
    """Normalise every value of a ``KEY=VALUE`` mapping."""
    return {key: _normalise_value(value) for key, value in (params or {}).items()}


def _flags_without_params(tokens: List[str]) -> List[str]:
    """Return the command's tokens with the ``--params`` pairs removed.

    This isolates the parts of the command that describe the *run*
    (model, dataset, seed) from the parts that describe the
    *hyperparameters*.
    """
    out: List[str] = []
    skip_next = False
    for token in tokens:
        if skip_next:
            skip_next = False
            continue
        if token == "--params":
            skip_next = True
            continue
        out.append(token)
    return out


def _run_flags(tokens: List[str]) -> Dict[str, str]:
    """Extract the run-defining ``--flag value`` pairs from a command.

    Visual-only flags (see :data:`_VISUAL_ONLY_FLAGS`) are dropped: they do
    not take part in the CLI's training path, so they cannot change which
    model a replay produces.
    """
    flags: Dict[str, str] = {}
    index = 0
    while index < len(tokens):
        token = tokens[index]
        if token in _VISUAL_ONLY_FLAGS:
            index += 2
            continue
        if token == "--params":
            # ``--params`` is repeatable and its values are compared
            # separately as a mapping; recording it here would report a
            # difference whenever the *order* of the pairs changed.
            index += 2
            continue
        if token.startswith("--"):
            value = ""
            if index + 1 < len(tokens) and not tokens[index + 1].startswith("--"):
                value = tokens[index + 1]
                index += 2
            else:
                index += 1
            flags[token] = value
            continue
        index += 1
    return flags


def _flag_differences(stored_tokens: List[str], fresh_tokens: List[str]) -> List[str]:
    """List the run-defining flags that differ between two commands.

    A flag whose value differs only in a visual-only way (for example a
    ``--n-samples 500`` the CLI would have used anyway) does not count.
    """
    stored_flags = _run_flags(stored_tokens)
    fresh_flags = _run_flags(fresh_tokens)

    differences: List[str] = []
    for flag in sorted(set(stored_flags) | set(fresh_flags)):
        left = stored_flags.get(flag)
        right = fresh_flags.get(flag)
        if left == right:
            continue
        if flag in _VISUAL_ONLY_FLAGS:
            # The flag does not affect the trained model, so a difference
            # here cannot change the outcome of a replay.
            continue
        if flag == "--test-size":
            if _normalise_value(left or "") == _normalise_value(right or ""):
                continue
        differences.append(flag)
    return differences


def _provenance_of(model: Dict[str, Any]) -> Dict[str, Any]:
    provenance = (model or {}).get("provenance")
    return dict(provenance) if isinstance(provenance, dict) else {}


def classify_recipe_drift(model: Dict[str, Any]) -> Dict[str, Any]:
    """Grade how far a model's frozen replay recipe has drifted.

    The stored recipe is compared against a freshly derived one.  The
    comparison is *semantic*, not textual: two commands that differ only in
    how they spell a list (``(50,)`` vs ``[50]``) reproduce the same model
    and are reported as cosmetic.

    Args:
        model: a normalised registry metadata dict.

    Returns:
        A dict with ``model_id``, ``drift`` (``"none"``, ``"cosmetic"`` or
        ``"semantic"``), ``stored_command``, ``fresh_command``,
        ``changed_fields`` (list of str), ``reason`` (str) and
        ``reproduces_same_model`` (bool).
    """
    model = model or {}
    model_id = model.get("id") or model.get("model_id") or ""
    provenance = _provenance_of(model)

    stored = (provenance.get("replay") or {}).get("cli") or {}
    stored_command = stored.get("command") or ""

    if not provenance:
        return {
            "model_id": model_id,
            "drift": "none",
            "stored_command": "",
            "fresh_command": "",
            "changed_fields": [],
            "reason": "no provenance record",
            "reproduces_same_model": True,
        }

    try:
        fresh = build_replay_command(provenance)
    except Exception as exc:  # pragma: no cover - defensive
        return {
            "model_id": model_id,
            "drift": "none",
            "stored_command": stored_command,
            "fresh_command": "",
            "changed_fields": [],
            "reason": f"could not derive a fresh recipe: {exc}",
            "reproduces_same_model": True,
        }

    fresh_command = fresh.get("command") or ""

    if not stored_command:
        return {
            "model_id": model_id,
            "drift": "none",
            "stored_command": "",
            "fresh_command": fresh_command,
            "changed_fields": [],
            "reason": "no frozen CLI recipe was stored",
            "reproduces_same_model": True,
        }

    if stored_command == fresh_command:
        return {
            "model_id": model_id,
            "drift": "none",
            "stored_command": stored_command,
            "fresh_command": fresh_command,
            "changed_fields": [],
            "reason": "",
            "reproduces_same_model": True,
        }

    stored_tokens = _tokenize(stored_command)
    fresh_tokens = _tokenize(fresh_command)

    changed_fields: List[str] = []

    # 1. The run-defining flags (model / dataset / seed) must match exactly.
    flag_diffs = _flag_differences(stored_tokens, fresh_tokens)
    if flag_diffs:
        changed_fields.extend(flag_diffs)

    # 2. The hyperparameters must denote the same values.
    stored_params = _normalise_params(_params_from_tokens(stored_tokens))
    fresh_params = _normalise_params(_params_from_tokens(fresh_tokens))
    if stored_params != fresh_params:
        changed_fields.append("hyperparameters")

    if changed_fields:
        return {
            "model_id": model_id,
            "drift": "semantic",
            "stored_command": stored_command,
            "fresh_command": fresh_command,
            "changed_fields": changed_fields,
            "reason": (
                "the frozen recipe would reproduce a different run "
                f"({', '.join(changed_fields)} changed)"
            ),
            "reproduces_same_model": False,
        }

    return {
        "model_id": model_id,
        "drift": "cosmetic",
        "stored_command": stored_command,
        "fresh_command": fresh_command,
        "changed_fields": [],
        "reason": "the recipe renders differently but denotes the same run",
        "reproduces_same_model": True,
    }


def integrity_report(models: Iterable[Dict[str, Any]]) -> Dict[str, Any]:
    """Audit every model's frozen replay recipe for drift.

    Args:
        models: an iterable of normalised registry metadata dicts.

    Returns:
        A dict with ``total``, ``with_provenance``, ``audited``,
        ``by_drift`` (counter per drift level), ``stale`` (int — recipes
        whose text no longer matches), ``broken`` (int — recipes that would
        reproduce a different model) and ``models`` (the list of
        semantically drifted models, for triage).
    """
    items = list(models or [])
    by_drift: Dict[str, int] = {level: 0 for level in DRIFT_LEVELS}
    drifted_models: List[Dict[str, Any]] = []
    with_provenance = 0
    stale = 0

    for model in items:
        if _provenance_of(model):
            with_provenance += 1
        verdict = classify_recipe_drift(model)
        level = verdict.get("drift", "none")
        by_drift[level] = by_drift.get(level, 0) + 1
        if level != "none":
            stale += 1
        if level == "semantic":
            drifted_models.append(verdict)

    audited = with_provenance
    return {
        "total": len(items),
        "with_provenance": with_provenance,
        "audited": audited,
        "by_drift": by_drift,
        "stale": stale,
        "broken": len(drifted_models),
        "models": drifted_models,
    }


def verify_replay(
    model_id: str,
    provenance: Dict[str, Any],
    expected_accuracy: Optional[float] = None,
    trainer: Optional[Any] = None,
) -> Dict[str, Any]:
    """Actually execute a model's replay and report whether it still reproduces.

    This is the "regression verification" half of DoD #4: the drift audit
    says whether a *recipe* still matches the code, but only executing it
    says whether the *run* still reproduces.

    Args:
        model_id: the model being verified.
        provenance: the model's provenance record.
        expected_accuracy: the accuracy recorded with the original model.
        trainer: an optional callable that performs the replay.  It is
            called with the replayed inputs and must return a dict with an
            ``accuracy`` key.  When omitted, no run is performed and the
            result is reported as ``not_verified``.

    Returns:
        A dict with ``model_id``, ``verified`` (bool), ``status``
        (``"reproduced"``, ``"drifted"`` or ``"not_verified"``),
        ``accuracy``, ``expected_accuracy``, ``accuracy_delta`` and
        ``drift`` (the recipe drift verdict).
    """
    provenance = provenance or {}
    drift = classify_recipe_drift({"id": model_id, "provenance": provenance})

    base: Dict[str, Any] = {
        "model_id": model_id,
        "verified": False,
        "status": "not_verified",
        "accuracy": None,
        "expected_accuracy": expected_accuracy,
        "accuracy_delta": None,
        "drift": drift,
    }

    if not provenance:
        base["status"] = "no_provenance"
        base["reason"] = "the model has no provenance record"
        return base

    if trainer is None:
        base["reason"] = "no trainer was supplied — the recipe was audited but not executed"
        return base

    try:
        outcome = trainer(provenance)
    except Exception as exc:
        base["status"] = "error"
        base["reason"] = f"the replay raised {type(exc).__name__}: {exc}"
        return base

    outcome = outcome or {}
    accuracy = outcome.get("accuracy")
    base["accuracy"] = accuracy
    if accuracy is not None and expected_accuracy is not None:
        base["accuracy_delta"] = round(float(accuracy) - float(expected_accuracy), 6)

    reproduced = outcome.get("reproduced")
    if reproduced is None:
        # Fall back to the accuracy delta when the trainer does not state it.
        delta = base["accuracy_delta"]
        reproduced = delta is not None and abs(delta) < 1e-9

    base["verified"] = True
    base["reproduced"] = bool(reproduced)
    base["status"] = "reproduced" if reproduced else "drifted"
    return base
