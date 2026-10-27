"""Backward-compatibility layer for artifacts pickled by older scikit-learn.

**Why this exists.**  The registry is a long-lived store.  Models
registered months ago were serialized by whatever scikit-learn version was
installed at the time, and joblib pickles are *not* guaranteed to stay
loadable across scikit-learn releases — scikit-learn itself documents this
under "Model persistence" and warns via ``InconsistentVersionWarning``.

Most version drift is harmless: the estimator classes keep their public
names, so an old pickle still resolves and merely warns.  But a small,
well-defined set of *internal* names were renamed between releases.  When
that happens the pickle's ``STACK_GLOBAL`` opcode points at a module path
that no longer contains the attribute, and unpickling raises::

    AttributeError: Can't get attribute '__pyx_unpickle_CyHalfBinomialLoss'
    on <module 'sklearn._loss._loss' ...>

Measured on a real registry (20713 models, 250 distinct blobs): **700
GradientBoosting models were unloadable** for exactly this reason.  The
artifacts were fine — the *name* had moved.  The old name was a Cython
internal (``__pyx_unpickle_CyHalfBinomialLoss``); scikit-learn 1.7.2
exposes it as the public ``CyHalfBinomialLoss``.

**What this module does.**  It installs a small table of legacy -> current
aliases onto the relevant modules, so that a pickle referring to the old
name resolves to the current class.  No artifact bytes are modified, no
model is re-serialized, and nothing is rewritten on disk.  The shim is
applied *at unpickle time only*, which means:

* stored artifacts stay byte-identical (the registry remains a faithful
  record of what was actually trained);
* the shim is idempotent and safe to apply repeatedly;
* if the current scikit-learn already provides the legacy name (i.e. we
  are running the version that created the artifact), the shim is a no-op.

**Scope discipline.**  The alias table only contains names that scikit-learn
itself renamed.  We do not monkey-patch estimator behaviour, do not
silently rewrite model attributes, and do not swallow the
``InconsistentVersionWarning`` — that warning is *informative*: the loaded
estimator was fitted under a different library version and its numerical
behaviour is not guaranteed to match.  Callers who need certainty should
re-train from the recorded provenance (see ``core/provenance.py``); this
module only makes the artifact *readable* again.

The module is imported for its side effect by :mod:`core.registry` and
:mod:`core.blob_store`, which are the two places in this codebase that
deserialize stored artifacts.  It is also safe to import directly and call
:func:`apply_shims` explicitly, e.g. in a standalone script that unpickles
artifacts without going through the registry.
"""
from __future__ import annotations

import importlib
import warnings
from typing import Dict, Iterable, List, Tuple


# ── alias table ────────────────────────────────────────────────────────────
#
# (module path, legacy attribute name, current attribute name)
#
# Each entry documents a rename performed by scikit-learn between the
# version that produced our oldest artifacts (1.4.x) and the version we
# run today.  ``legacy`` is the name written into the pickle; ``current``
# is what the installed scikit-learn exposes today.  Both must resolve for
# the alias to be installed.

_ALIASES: Tuple[Tuple[str, str, str], ...] = (
    # sklearn._loss._loss: Cython internal name -> public name.
    # Introduced in 1.4.x as a private implementation detail, renamed to
    # the public `CyHalfBinomialLoss` in later releases.
    ("sklearn._loss._loss", "__pyx_unpickle_CyHalfBinomialLoss", "CyHalfBinomialLoss"),
)


def _resolve(module_path: str, name: str):
    """Import ``module_path`` and return ``(module, attribute)`` or ``(None, None)``."""
    try:
        module = importlib.import_module(module_path)
    except Exception:  # pragma: no cover - only if scikit-learn layout changes
        return None, None
    return module, getattr(module, name, None)


def apply_shims() -> List[str]:
    """Install legacy-name aliases for renamed scikit-learn internals.

    Returns a list of human-readable descriptions of the aliases that were
    actually installed during *this* call.  Calling this repeatedly is
    safe: already-installed aliases are skipped and not reported again.

    The function never raises for a missing or unimportable module — a
    renamed-away module simply means there is nothing to alias, and the
    pickle in question would fail for a different (and genuinely
    unfixable) reason.
    """
    installed: List[str] = []

    for module_path, legacy, current in _ALIASES:
        module, current_attr = _resolve(module_path, current)
        if module is None or current_attr is None:
            # The installed scikit-learn does not have the current name
            # either — nothing to alias (this can happen on very old
            # scikit-learn releases where the legacy name is the *only*
            # name and the pickle is already loadable).
            continue

        if hasattr(module, legacy):
            # Already present (either because scikit-learn still exports
            # it, or because we installed it on an earlier call).
            continue

        try:
            setattr(module, legacy, current_attr)
        except Exception:  # pragma: no cover - read-only module objects
            continue

        installed.append(f"{module_path}.{legacy} -> {current}")

    return installed


def installed_aliases() -> Dict[str, str]:
    """Return the currently active alias table as ``{legacy dotted path: current}``."""
    active: Dict[str, str] = {}
    for module_path, legacy, current in _ALIASES:
        module, _ = _resolve(module_path, current)
        if module is None:
            continue
        if hasattr(module, legacy):
            active[f"{module_path}.{legacy}"] = current
    return active


def is_compat_shim_active() -> bool:
    """Return ``True`` when at least one legacy alias is currently installed."""
    return bool(installed_aliases())


def check_artifact(path) -> Tuple[bool, str]:
    """Probe whether ``path`` can be deserialized under the current runtime.

    Returns ``(ok, message)``.  This is a *diagnostic* helper — it never
    raises for a broken artifact, and it never modifies the file.

    It is intended for registry health checks ("how many of my stored
    models are actually loadable right now?"), not as a replacement for
    loading the model.
    """
    import joblib

    try:
        joblib.load(path)
    except Exception as exc:  # noqa: BLE001 - diagnostic must not raise
        return False, f"{type(exc).__name__}: {exc}"
    return True, "ok"


# Apply the shims at import time.  Importing this module is the documented
# way to opt in; every consumer of stored artifacts in this codebase
# imports it (directly or transitively via core.registry).
apply_shims()
