"""Provenance coverage reporting for v13 DoD #3.

DoD #1 records provenance, DoD #2 makes it replayable.  But a registry is
only trustworthy if you know *how much* of it is covered: how many models
carry a provenance record, how many of those have a replay plan, and how
many of those are actually reproducible right now.

This module answers exactly that question and nothing more.  It is a read-only
audit surface:

* :func:`provenance_coverage` — per-model coverage classification.
* :func:`coverage_summary` — aggregated counters + percentages.
* :func:`replayability_report` — the reasons a model is *not* replayable,
  grouped by cause, so the fix is obvious.

Nothing here mutates the registry, and no legacy model is rewritten — the
audit must be safe to run against a registry full of pre-v13 records.
"""
from __future__ import annotations

from typing import Any, Dict, Iterable, List, Optional, Tuple

from core.provenance import build_replay_command

__all__ = [
    "COVERAGE_STATUSES",
    "classify_model",
    "provenance_coverage",
    "coverage_summary",
    "replayability_report",
]

#: Every coverage state a registered model can be in.
COVERAGE_STATUSES: Tuple[str, ...] = (
    "replayable_exact",   # provenance + replay plan + CLI command is exact
    "replayable_sdk",     # provenance + replay plan, but CLI command is lossy
    "provenance_only",    # provenance present, no replay plan derivable
    "no_provenance",      # registered before v13 — nothing recorded
)

#: Coverage states that count as "the model can be reproduced".
_REPRODUCIBLE = frozenset({"replayable_exact", "replayable_sdk"})


def _provenance_of(model: Dict[str, Any]) -> Dict[str, Any]:
    provenance = model.get("provenance")
    return dict(provenance) if isinstance(provenance, dict) else {}


def classify_model(model: Dict[str, Any], replay_plan: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Classify a single registered model by provenance coverage.

    Args:
        model: a normalised registry metadata dict.
        replay_plan: the replay plan for this model, if the caller already
            resolved it.  When omitted the plan is derived from the frozen
            snapshot only, which undercounts models registered during
            DoD #1 (their plan is derivable on demand).  Callers that have
            registry access should pass the resolved plan.

    Returns:
        A dict with ``model_id``, ``status``, ``provenance`` (bool),
        ``replay`` (bool), ``cli_exact`` (bool), ``fingerprint`` (str|None)
        and ``reason`` (str, set when the model is not replayable).
    """
    model = model or {}
    model_id = model.get("id") or model.get("model_id") or ""
    provenance = _provenance_of(model)

    if not provenance:
        return {
            "model_id": model_id,
            "status": "no_provenance",
            "provenance": False,
            "replay": False,
            "cli_exact": False,
            "fingerprint": None,
            "reason": "registered before v13 — no provenance record",
        }

    # Prefer the plan resolved by the caller (which knows how to derive one
    # for models registered before DoD #2); fall back to the frozen
    # snapshot stored in the provenance record.
    if replay_plan is None:
        frozen = provenance.get("replay")
        replay_plan = frozen if isinstance(frozen, dict) else None

    sdk = (replay_plan or {}).get("sdk")
    if not sdk:
        return {
            "model_id": model_id,
            "status": "provenance_only",
            "provenance": True,
            "replay": False,
            "cli_exact": False,
            "fingerprint": provenance.get("fingerprint"),
            "reason": "provenance present but no replay plan could be derived",
        }

    cli = (replay_plan or {}).get("cli") or {}
    cli_exact = bool(cli.get("exact"))
    if cli_exact:
        status = "replayable_exact"
        reason = ""
    else:
        status = "replayable_sdk"
        warnings = cli.get("warnings") or []
        reason = warnings[0] if warnings else "CLI command is not exact; use the SDK recipe"

    return {
        "model_id": model_id,
        "status": status,
        "provenance": True,
        "replay": True,
        "cli_exact": cli_exact,
        "fingerprint": provenance.get("fingerprint"),
        "reason": reason,
    }


def provenance_coverage(
    models: Iterable[Dict[str, Any]],
    replay_plans: Optional[Dict[str, Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """Classify every model in ``models``.

    Args:
        models: an iterable of normalised registry metadata dicts.
        replay_plans: an optional mapping of ``model_id`` to the resolved
            replay plan.  Supplying it makes the audit count models
            registered before DoD #2 as replayable, which is what the
            registry's own ``get_replay_plan()`` would report.

    Returns:
        A list of classification dicts, one per model, in input order.
    """
    plans = replay_plans or {}
    out = []
    for model in models:
        model_id = model.get("id") or model.get("model_id") or ""
        out.append(classify_model(model, plans.get(model_id)))
    return out


def coverage_summary(
    models: Iterable[Dict[str, Any]],
    replay_plans: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Aggregate provenance coverage over a set of registered models.

    Args:
        models: an iterable of normalised registry metadata dicts.
        replay_plans: an optional mapping of ``model_id`` to resolved replay
            plans (see :func:`provenance_coverage`).

    Returns:
        A dict with ``total``, ``by_status`` (counter per status),
        ``with_provenance``, ``with_replay``, ``cli_exact``,
        ``reproducible`` and the derived percentages.
    """
    classifications = provenance_coverage(models, replay_plans)
    total = len(classifications)

    by_status: Dict[str, int] = {status: 0 for status in COVERAGE_STATUSES}
    for item in classifications:
        by_status[item["status"]] = by_status.get(item["status"], 0) + 1

    with_provenance = sum(1 for c in classifications if c["provenance"])
    with_replay = sum(1 for c in classifications if c["replay"])
    cli_exact = sum(1 for c in classifications if c["cli_exact"])
    reproducible = sum(1 for c in classifications if c["status"] in _REPRODUCIBLE)

    def _pct(count: int) -> float:
        return round(count * 100.0 / total, 2) if total else 0.0

    return {
        "total": total,
        "by_status": by_status,
        "with_provenance": with_provenance,
        "with_replay": with_replay,
        "cli_exact": cli_exact,
        "reproducible": reproducible,
        "coverage_pct": _pct(with_provenance),
        "replayable_pct": _pct(reproducible),
        "cli_exact_pct": _pct(cli_exact),
    }


def replayability_report(
    models: Iterable[Dict[str, Any]],
    replay_plans: Optional[Dict[str, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Explain *why* models are not replayable, grouped by cause.

    This is the actionable half of the coverage audit: a bare "37% covered"
    number does not tell a maintainer what to do, but "412 models lack a
    provenance record (they predate v13) and 89 have a lossy CLI command
    (use the SDK recipe)" does.

    Args:
        models: an iterable of normalised registry metadata dicts.
        replay_plans: an optional mapping of ``model_id`` to resolved replay
            plans (see :func:`provenance_coverage`).

    Returns:
        A dict with ``total``, ``reproducible``, ``blocked`` and
        ``reasons`` (a list of ``{reason, count, models}`` entries, most
        common cause first).
    """
    classifications = provenance_coverage(models, replay_plans)

    groups: Dict[str, List[str]] = {}
    for item in classifications:
        if item["status"] in _REPRODUCIBLE:
            continue
        reason = item.get("reason") or "unknown"
        groups.setdefault(reason, []).append(item["model_id"])

    reasons = [
        {"reason": reason, "count": len(model_ids), "models": model_ids}
        for reason, model_ids in sorted(groups.items(), key=lambda kv: (-len(kv[1]), kv[0]))
    ]

    return {
        "total": len(classifications),
        "reproducible": sum(1 for c in classifications if c["status"] in _REPRODUCIBLE),
        "blocked": sum(len(v) for v in groups.values()),
        "reasons": reasons,
    }


def cli_replay_check(model: Dict[str, Any]) -> Dict[str, Any]:
    """Re-derive the CLI replay command for a model and report its fidelity.

    Used by the audit to detect a stale replay snapshot: the plan frozen at
    registration time may no longer match what today's code would emit
    (for example after the CLI's ``--params`` parser changed).

    Args:
        model: a normalised registry metadata dict.

    Returns:
        A dict with ``available`` (bool), ``exact`` (bool) and
        ``drifted`` (bool — the stored snapshot disagrees with the freshly
        derived command).
    """
    provenance = _provenance_of(model)
    if not provenance:
        return {"available": False, "exact": False, "drifted": False}

    stored = provenance.get("replay")
    stored_cli = (stored or {}).get("cli") if isinstance(stored, dict) else None

    try:
        fresh = build_replay_command(provenance)
    except Exception:
        return {"available": True, "exact": False, "drifted": False}

    drifted = False
    if isinstance(stored_cli, dict):
        drifted = bool(stored_cli.get("command")) and stored_cli.get("command") != fresh.get("command")

    return {
        "available": True,
        "exact": bool(fresh.get("exact")),
        "drifted": drifted,
        "command": fresh.get("command"),
        "warnings": fresh.get("warnings") or [],
    }
