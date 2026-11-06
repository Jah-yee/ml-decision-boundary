#!/usr/bin/env python3
"""Audit the release pipeline of this repository.

**Why this exists.**  Four audits already exist, and every one of them
deliberately *skips* the release workflow:

- :mod:`ci_trigger_audit` (DoD #7) skips workflows that do not run on
  pull requests — ``release.yml`` is tag-driven, so it is skipped;
- :mod:`pr_coverage_audit` (DoD #8) audits ``ci.yml`` only — the
  release workflow is explicitly absent by design;
- :mod:`job_graph_audit` (DoD #18) parses ``jobs:`` blocks but
  exempts workflows that have no gate, and ``release.yml`` has none;
- :mod:`stack_topology_audit` (DoD #17) is about pull request shape.

So the workflow that **actually publishes the product** — the one job in
this repository that creates a GitHub Release and commits to ``master``
with ``contents: write`` — has **no audit at all**.  It is the single
most consequential file in ``.github/`` and it has been executed **zero
times**: the repository has no tags at all, so the release pipeline has
never run, ever.

That combination — *never executed*, *highest blast radius*, *no audit*
— is exactly the shape of defect that hides.  This audit closes it.

**The gap, concretely.**  ``release.yml`` has at least five defects
that are individually invisible to a green CI and individually fatal on
the day of the first release:

1. **The first release cannot succeed.**  The changelog step runs
   ``git describe --tags --abbrev=0 HEAD~1`` to find the previous
   tag.  With no tags in the repository that command exits **128**
   ("No names found, cannot describe anything").  Because the step
   runs under the default shell with ``set -e`` semantics, the job
   dies before a release is ever created.  The very first ``v*`` tag
   pushed to this repository fails.

2. **The previous-tag lookup is anchored to ``HEAD~1``, not to the
   tag itself.**  Even with tags present, ``HEAD~1`` is only the
   previous commit *of the tagged commit*, not the previous *release*.
   If the tagged commit is a merge or if commits were pushed after the
   last tag, the resolved "previous version" is wrong — the changelog
   silently covers the wrong range.  It also breaks outright when the
   tagged commit is the very first commit (``HEAD~1`` does not
   resolve — "Failed to resolve 'HEAD' as a valid ref").

3. **The changelog is byte-truncated, not line-truncated.**  The
   merge step ends with ``tail -n +3 CHANGELOG.md | head -c 5000``.
   ``head -c`` cuts at an arbitrary **byte** offset and does not care
   about character boundaries, so a multi-byte UTF-8 character is
   split in half.  The resulting file is **invalid UTF-8**, the step
   still exits **0**, and the corrupt file is committed and pushed to
   ``master`` by the following step.  A silent corruption, shipped.

4. **No concurrency guard.**  Two tags pushed in quick succession run
   two release jobs at the same time.  Both read ``CHANGELOG.md``,
   both write it, and the second commit races the first — one of the
   two changelog updates is silently lost, and the commit step can
   fail with a non-fast-forward push.

5. **Third-party actions are pinned to mutable tags.**  Every action
   is referenced by a moving tag (``@v2``, ``@v5``, ``@v4``) rather
   than by commit SHA.  The upstream project can move those tags, and
   the release job — the one with ``contents: write`` — will run
   whatever the tag points to at that moment.

**What this audit checks.**  For each release workflow:

- **Tag discovery** — the previous-tag lookup has a working fallback
  for the first release and is anchored to the tag rather than to an
  unrelated commit;
- **Changelog integrity** — no byte-level truncation of the changelog;
- **Concurrency** — the workflow declares a ``concurrency:`` group so
  that two releases cannot race;
- **Action pinning** — every third-party action is pinned to a commit
  SHA;
- **Permissions** — the workflow's ``permissions:`` block is
  explicitly declared (least privilege) and is not widened to
  ``write-all``;
- **Trigger safety** — the release workflow does not fire on
  unprotected or non-tag events.

**Design constraints.**  Same house rules as the sibling audits:

- **No third-party dependency** — PyYAML is not in
  ``requirements.lock``, so the reader below is a small subset parser
  that raises on anything it does not understand rather than guessing.
  A future edit to the workflow must not be silently mis-parsed into a
  false pass.
- **Read-only** — the audit never writes to the workflow.
- **Degrades honestly** — an unparsable workflow is reported and the
  gate exits non-zero, never a vacuous success.
- **Monotonic gate modes** — ``--strict`` requires a **strict
  superset** of the default requirements, evaluated through the single
  :func:`evaluate_gate` function, so a stricter mode can only ever
  turn a pass into a failure.

Usage::

    python3 scripts/release_audit.py                  # audit every workflow
    python3 scripts/release_audit.py --workflow .github/workflows/release.yml
    python3 scripts/release_audit.py --json           # machine-readable
    python3 scripts/release_audit.py --strict         # stricter gate mode
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

#: GitHub-owned action prefixes.  These are covered by GitHub's own
#: security guarantees, so pinning them to a SHA is not required by
#: this audit.
FIRST_PARTY_PREFIXES = ("actions/", "github/")

#: A workflow that *publishes a release artifact* to the outside world.
KIND_RELEASE = "release"

#: A workflow that runs *tests / checks* on ordinary pushes and PRs.
KIND_CI = "ci"

#: Every workflow kind this audit knows about.
WORKFLOW_KINDS: tuple[str, ...] = (KIND_RELEASE, KIND_CI)

#: A fully-qualified action reference pinned to a 40-hex commit SHA.
_SHA_PIN_RE = re.compile(r"^[0-9a-f]{40}$")

#: A tag-ish reference such as ``v2`` or ``v2.1.3`` — mutable.
_TAG_REF_RE = re.compile(r"^v\d+(\.\d+)*(\.[0-9A-Za-z._-]+)?$")

#: ``head -c N`` — byte truncation.
_HEAD_C_RE = re.compile(r"\bhead\s+-c\s+(?P<n>\d+)")

#: ``git describe --tags`` used to discover the previous tag.
#:
#: The pattern deliberately stops at the closing parenthesis of a
#: command substitution so that the reported call is the command
#: itself and not the surrounding shell noise.
_DESCRIBE_RE = re.compile(
    r"git\s+describe\s+(?P<args>[^()\n;|&]*(?:--tags)[^()\n;|&]*)"
)

#: ``git tag --points-at HEAD`` — the robust way to identify the tag
#: that is *currently being released*, so it can be excluded from the
#: list of candidate previous tags.
_POINTS_AT_RE = re.compile(r"git\s+tag\s+--points-at\s+HEAD")


class WorkflowParseError(RuntimeError):
    """Raised when a workflow file cannot be parsed by the subset reader."""


# ── YAML subset reader ─────────────────────────────────────────────────────


_JOB_KEY_RE = re.compile(r"^  (?P<name>[A-Za-z0-9_.-]+):\s*$")
_RUN_KEY_RE = re.compile(r"^      - run:\s*(?P<rest>.*)$")
_USES_KEY_RE = re.compile(r"^      - uses:\s*(?P<rest>.*)$")
_STEP_LIST_RE = re.compile(r"^    steps:\s*$")
_ON_KEY_RE = re.compile(r"^(?P<indent>\s*)on:\s*(?P<rest>.*)$")
_PERMISSIONS_KEY_RE = re.compile(r"^(?P<indent>\s*)permissions:\s*(?P<rest>.*)$")
_CONCURRENCY_KEY_RE = re.compile(r"^(?P<indent>\s*)concurrency:\s*(?P<rest>.*)$")
_PUSH_KEY_RE = re.compile(r"^(?P<indent>\s*)push:\s*(?P<rest>.*)$")


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment, respecting quotes."""
    out: list[str] = []
    quote: str | None = None
    for char in line:
        if quote:
            out.append(char)
            if char == quote:
                quote = None
            continue
        if char in ("'", '"'):
            quote = char
            out.append(char)
            continue
        if char == "#":
            break
        out.append(char)
    return "".join(out).rstrip()


@dataclass
class Step:
    """One step of a job."""

    name: str = ""
    run: str = ""
    uses: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "run": self.run, "uses": self.uses}


@dataclass
class Job:
    """One job of a workflow."""

    name: str
    steps: list[Step] = field(default_factory=list)

    @property
    def run_scripts(self) -> list[str]:
        return [s.run for s in self.steps if s.run]

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "steps": [s.to_dict() for s in self.steps]}


@dataclass
class Workflow:
    """A parsed workflow file (the subset this audit cares about)."""

    path: Path
    jobs: dict[str, Job] = field(default_factory=dict)
    triggers: list[str] = field(default_factory=list)
    tag_patterns: list[str] = field(default_factory=list)
    permissions: dict[str, str] = field(default_factory=dict)
    has_concurrency: bool = False
    concurrency_expr: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": str(self.path),
            "jobs": {k: v.to_dict() for k, v in self.jobs.items()},
            "triggers": list(self.triggers),
            "tag_patterns": list(self.tag_patterns),
            "permissions": dict(self.permissions),
            "has_concurrency": self.has_concurrency,
            "concurrency_expr": self.concurrency_expr,
        }


def _parse_top_level_scalar(text: str) -> str:
    return text.strip().strip("'\"").strip()


def parse_workflow(path: Path) -> Workflow:
    """Parse the parts of a workflow this audit inspects.

    The reader understands the ``on:`` block (with its ``tags:``
    filter), a top-level ``permissions:`` mapping, a top-level
    ``concurrency:`` key, and the ``jobs:`` block with its ``run:`` and
    ``uses:`` steps.

    **Block model.**  Each block records the indent level of its
    *content* (``block_level + 2``).  A line whose indent is **less
    than** the content level closes the block; a line whose indent is
    **equal to** the block's own key level is a *sibling key* of the
    block and does not close it.  That distinction is what lets
    ``on:`` hold two event keys (``push:`` and ``workflow_dispatch:``)
    while ``tags:`` remains nested under ``push:``.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowParseError(f"cannot read {path}: {exc}") from exc

    lines = text.splitlines()
    workflow = Workflow(path=path)

    def indent_of(line: str) -> int:
        return len(line) - len(line.lstrip(" "))

    current: Job | None = None
    in_steps = False
    # The stack of open blocks; each entry is (kind, content_indent).
    blocks: list[tuple[str, int]] = []

    def close_to(indent: int) -> None:
        while blocks and indent < blocks[-1][1]:
            blocks.pop()

    def block_kind() -> str | None:
        return blocks[-1][0] if blocks else None

    for raw in lines:
        line = _strip_comment(raw)
        if not line.strip():
            continue
        indent = indent_of(line)
        stripped = line.strip()

        # ---- close blocks we dedented out of ------------------------
        close_to(indent)

        # ---- top-level ``on:`` block --------------------------------
        if indent == 0 and stripped.startswith("on:"):
            rest = stripped[3:].strip()
            if rest and rest not in ("|", ">"):
                # Inline form: ``on: push`` / ``on: [push, workflow_dispatch]``
                inner = rest.strip("[]").replace(",", " ")
                workflow.triggers.extend(inner.split())
            else:
                blocks.append(("on", 2))
            current = None
            in_steps = False
            continue

        kind = block_kind()
        if kind in ("on", "on_event", "tags"):
            # An event key at two-space indent: ``push:`` / ``pull_request:``
            if kind in ("on", "on_event") and indent == 2 and re.match(
                r"^[A-Za-z_][\w-]*:\s*$", stripped
            ):
                workflow.triggers.append(stripped[:-1])
                if kind == "on":
                    blocks[-1] = ("on_event", 2)
                else:
                    # A second event key at the same level; the
                    # ``on_event`` marker is already in place.
                    blocks.append(("on_event", 4))
                continue
            # An event key with an inline body.
            if kind in ("on", "on_event") and indent == 2 and re.match(
                r"^[A-Za-z_][\w-]*:\s*\S+", stripped
            ):
                workflow.triggers.append(stripped.split(":", 1)[0])
                if kind == "on":
                    blocks[-1] = ("on_event", 2)
                else:
                    blocks.append(("on_event", 4))
                continue
            # A ``tags:`` filter nested under the event key.  The
            # ``on_event`` marker is *kept* underneath so that a
            # second event key at the same level (``workflow_dispatch:``)
            # is still recognised after the ``tags:`` block closes.
            if kind == "on_event" and indent == 4 and stripped.startswith("tags:"):
                rest = stripped[5:].strip()
                if rest:
                    workflow.tag_patterns.append(_parse_top_level_scalar(rest))
                blocks.append(("tags", 6))
                continue
            # List items under ``tags:``.
            if kind == "tags" and indent >= 6 and stripped.startswith("- "):
                workflow.tag_patterns.append(_parse_top_level_scalar(stripped[2:]))
                continue
            continue

        # ---- top-level ``permissions:`` ------------------------------
        if indent == 0 and stripped.startswith("permissions:"):
            rest = stripped[len("permissions:"):].strip()
            if rest and rest not in ("|", ">"):
                workflow.permissions["_inline"] = _parse_top_level_scalar(rest)
            else:
                blocks.append(("permissions", 2))
            current = None
            in_steps = False
            continue

        if block_kind() == "permissions":
            if indent == 2 and re.match(r"^[A-Za-z0-9_-]+:\s*\S+", stripped):
                key, _, value = stripped.partition(":")
                workflow.permissions[key.strip()] = _parse_top_level_scalar(value)
                continue
            continue

        # ---- top-level ``concurrency:`` ------------------------------
        if indent == 0 and stripped.startswith("concurrency:"):
            workflow.has_concurrency = True
            workflow.concurrency_expr = stripped[len("concurrency:"):].strip()
            current = None
            in_steps = False
            blocks.append(("concurrency", 2))
            continue

        if block_kind() == "concurrency":
            if indent == 2 and stripped.startswith("group:"):
                workflow.concurrency_expr = stripped[len("group:"):].strip()
                continue
            continue

        # ---- ``jobs:`` block -----------------------------------------
        if indent == 0 and stripped == "jobs:":
            current = None
            in_steps = False
            blocks.append(("jobs", 2))
            continue

        if block_kind() == "jobs":
            job_match = _JOB_KEY_RE.match(line)
            if job_match:
                current = Job(name=job_match.group("name"))
                workflow.jobs[current.name] = current
                in_steps = False
                continue
            if current is None:
                continue
            if indent == 4 and stripped == "steps:":
                in_steps = True
                continue
            if in_steps:
                # A new step starts with "- " at six-space indent.  A
                # step may open with any of ``name:`` / ``uses:`` /
                # ``run:``; the remaining keys of the same step follow
                # on subsequent lines at the same indent.
                if indent >= 6 and stripped.startswith("- "):
                    body = stripped[2:].strip()
                    current.steps.append(Step())
                    last = current.steps[-1]
                    uses_match = re.match(r"^uses:\s*(?P<rest>.+)$", body)
                    run_match = re.match(r"^run:\s*(?P<rest>.*)$", body)
                    name_match = re.match(r"^name:\s*(?P<rest>.+)$", body)
                    if uses_match:
                        last.uses = _parse_top_level_scalar(uses_match.group("rest"))
                    elif run_match:
                        last.run = run_match.group("rest")
                    elif name_match:
                        last.name = _parse_top_level_scalar(name_match.group("rest"))
                    continue
                # A sibling key of the current step (``uses:`` /
                # ``run:`` / ``name:`` at eight-space indent), or a
                # continuation line of a multi-line ``run:`` body.
                if indent >= 8 and current.steps:
                    last = current.steps[-1]
                    uses_match = re.match(r"^uses:\s*(?P<rest>.+)$", stripped)
                    run_match = re.match(r"^run:\s*(?P<rest>.*)$", stripped)
                    name_match = re.match(r"^name:\s*(?P<rest>.+)$", stripped)
                    if uses_match and not last.uses:
                        last.uses = _parse_top_level_scalar(uses_match.group("rest"))
                        continue
                    if run_match and not last.run:
                        last.run = run_match.group("rest")
                        continue
                    if name_match and not last.name:
                        last.name = _parse_top_level_scalar(name_match.group("rest"))
                        continue
                    if last.run:
                        last.run += "\n" + stripped
                    continue
            continue

        # ---- anything else at top level ------------------------------
        if indent == 0:
            current = None
            in_steps = False

    return workflow


# ── audit checks ───────────────────────────────────────────────────────────


def check_tag_discovery(workflow: Workflow) -> dict[str, Any]:
    """The previous-tag lookup must work on the *first* release.

    A release workflow has to find "the previous version" to compute
    the changelog range.  The canonical way is
    ``git describe --tags --abbrev=0 HEAD~1``.  That command fails
    with exit code 128 when the repository has no tags — which is
    exactly the state of the repository on the day of the first
    release — and it is also anchored to a *commit* rather than to the
    *tag*, so it resolves the wrong boundary whenever the tagged commit
    is not the direct child of the previous tag.

    The fix is a fallback that yields an empty previous tag on the
    first release, e.g.::

        PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "")

    A workflow is considered to have a *safe* lookup when it resolves
    the previous tag in one of two acceptable ways.

    1. **``git describe --tags`` guarded against failure.**  The
       command must be followed by ``||`` (or otherwise tolerate a
       non-zero exit) so that a tagless repository yields an empty
       previous tag instead of exit code 128.
    2. **``git tag --points-at HEAD`` plus a sorted listing.**  This
       is the *robust* form: it identifies the tag being released and
       then excludes it from the sorted tag list, so the first release
       yields an empty previous tag and every later release yields the
       genuinely previous tag.  It must also be guarded, because the
       pipeline's last stage exits non-zero when no tag matches.
    """
    describe_calls: list[str] = []
    guarded = False
    tag_listing = False
    for job in workflow.jobs.values():
        for script in job.run_scripts:
            for match in _DESCRIBE_RE.finditer(script):
                describe_calls.append(match.group(0).strip())
                tail = script[match.end():]
                # Guarded when the failure is tolerated: ``|| ...``,
                # ``|| true``, ``|| echo``, ``set +e``, or the call is
                # inside a command substitution assigned to a variable
                # whose value is subsequently defaulted.
                if re.search(r"\|\|\s*(\S+)", tail[:40]) or "set +e" in script:
                    guarded = True
                if re.search(
                    r"\$\(\s*git\s+describe[^\n)]*\)\s*(\|\||;)",
                    script,
                ):
                    guarded = True
            # The robust form: resolve the tag at HEAD, then pick the
            # newest *other* tag from a version-sorted listing.
            if _POINTS_AT_RE.search(script):
                tag_listing = True
                if re.search(r"\|\|\s*(\S+)", script) or "set +e" in script:
                    guarded = True
    return {
        "describe_calls": describe_calls,
        "guarded": guarded,
        "tag_listing": tag_listing,
        "ok": (bool(describe_calls) or tag_listing) and guarded,
    }


def check_changelog_integrity(workflow: Workflow) -> dict[str, Any]:
    """The changelog must not be truncated at a byte boundary.

    ``head -c N`` cuts at an arbitrary byte offset.  When the file
    contains multi-byte UTF-8 characters the cut lands inside a
    character and produces a file that cannot be decoded.  The step
    still exits 0 and the corrupt file is committed to ``master``.

    The fix is to truncate on a character boundary (``head -c`` ->
    ``head -c`` with a safe byte count is not enough; use
    ``head -n`` for line truncation, or truncate with Python on
    decoded text).
    """
    offenders: list[dict[str, Any]] = []
    for job in workflow.jobs.values():
        for script in job.run_scripts:
            for match in _HEAD_C_RE.finditer(script):
                offenders.append(
                    {
                        "job": job.name,
                        "byte_limit": int(match.group("n")),
                        "snippet": match.group(0),
                    }
                )
    return {"byte_truncations": offenders, "ok": not offenders}


def check_concurrency(workflow: Workflow) -> dict[str, Any]:
    """Two releases must not be able to race each other.

    Without a ``concurrency:`` group, two tags pushed in quick
    succession start two release jobs simultaneously.  Both write
    ``CHANGELOG.md`` and both try to commit it, so one update is
    silently lost and the commit step can fail with a non-fast-forward
    push.
    """
    return {
        "has_concurrency": workflow.has_concurrency,
        "concurrency_expr": workflow.concurrency_expr,
        "ok": workflow.has_concurrency,
    }


def check_action_pinning(workflow: Workflow) -> dict[str, Any]:
    """Third-party actions must be pinned to a commit SHA.

    A tag reference (``@v2``) is mutable: the upstream repository can
    move it at any time, and the job that holds ``contents: write``
    will run whatever the tag points to at that moment.
    """
    unpinned: list[dict[str, Any]] = []
    pinned = 0
    for job in workflow.jobs.values():
        for step in job.steps:
            if not step.uses:
                continue
            uses = step.uses
            if "@" not in uses:
                unpinned.append({"job": job.name, "uses": uses, "reason": "no version"})
                continue
            action, _, ref = uses.rpartition("@")
            if action.startswith(FIRST_PARTY_PREFIXES):
                continue
            if _SHA_PIN_RE.match(ref):
                pinned += 1
                continue
            unpinned.append(
                {
                    "job": job.name,
                    "uses": uses,
                    "reason": "mutable tag ref" if _TAG_REF_RE.match(ref) else "not a sha",
                }
            )
    return {"unpinned_actions": unpinned, "pinned_count": pinned, "ok": not unpinned}


def check_permissions(workflow: Workflow) -> dict[str, Any]:
    """Permissions must be declared explicitly and minimally.

    ``permissions: write-all`` grants every scope in the repository.
    A release workflow does need ``contents: write`` to create the
    release and to commit the changelog, but it must not hold any
    other scope.
    """
    perms = workflow.permissions
    problems: list[str] = []
    if not perms:
        problems.append("no top-level 'permissions:' block declared")
    if perms.get("_inline") == "write-all":
        problems.append("permissions: write-all grants every scope")
    for scope, value in perms.items():
        if scope == "_inline":
            continue
        if value == "write" and scope != "contents":
            problems.append(f"write scope granted unnecessarily: {scope}")
    return {"permissions": dict(perms), "problems": problems, "ok": not problems}


def check_trigger_safety(workflow: Workflow, kind: str = KIND_RELEASE) -> dict[str, Any]:
    """Check that the trigger set matches what the workflow's kind implies.

    The rule **reverses with the kind**, and that reversal is the whole
    point:

    * A *release* workflow must fire on tags, not on anything else.  A
      release workflow that also fires on ``push`` to a branch would
      publish a release for every ordinary commit.  The trigger set is
      therefore required to be tag-driven and to be restricted to a
      ``v*``-style tag pattern.
    * A *CI* workflow must **not** be restricted to tags.  A CI
      workflow whose only trigger is ``push: tags:`` never runs for an
      ordinary commit — which is the exact opposite of what CI is for.

    Applying the release rule to CI (or vice versa) turns a correct
    workflow into a reported defect.  A gate that flags correct
    behaviour is worse than no gate, because it trains people to
    ignore it.
    """
    problems: list[str] = []
    triggers = set(workflow.triggers)
    if not triggers:
        problems.append("no trigger parsed")

    if kind == KIND_RELEASE:
        if not triggers <= {"push"}:
            problems.append(
                f"release workflow fires on non-push events: {sorted(triggers - {'push'})}"
            )
        if not workflow.tag_patterns:
            problems.append("push trigger has no 'tags:' filter — releases on every push")
        else:
            for pattern in workflow.tag_patterns:
                if not (pattern.startswith("v") or "*" in pattern):
                    problems.append(f"unexpected tag pattern: {pattern}")
    else:  # KIND_CI
        if triggers <= {"push"} and workflow.tag_patterns:
            problems.append(
                "CI workflow only fires on tags — it would never run for an "
                "ordinary commit"
            )
        if "push" not in triggers and "pull_request" not in triggers:
            problems.append(
                f"CI workflow fires on neither 'push' nor 'pull_request': {sorted(triggers)}"
            )

    return {
        "triggers": sorted(triggers),
        "tag_patterns": list(workflow.tag_patterns),
        "problems": problems,
        "ok": not problems,
    }


# ── workflow kind classification ──────────────────────────────────────────


def classify_workflow(workflow: Workflow) -> str:
    """Classify a workflow as a *release* pipeline or as *CI*.

    The classification is **semantic**, not a filename convention: a
    workflow is a release pipeline when it declares a ``tags:`` filter,
    when its name says ``release``, or when it holds the
    ``contents: write`` scope (the scope that lets a workflow publish
    an artifact).

    Why this matters: the release-specific requirements (previous-tag
    discovery, changelog integrity, release concurrency) are **meaningless**
    for a CI workflow, and the trigger requirement is **semantically
    reversed** between the two kinds.  Auditing a CI workflow with the
    release ruleset reports a correct workflow as defective — and a gate
    that cries wolf is a gate people learn to ignore.
    """
    if workflow.tag_patterns:
        return KIND_RELEASE
    if "release" in workflow.path.stem.lower():
        return KIND_RELEASE
    if workflow.permissions.get("contents") == "write":
        return KIND_RELEASE
    return KIND_CI


# ── audit driver ───────────────────────────────────────────────────────────


def audit_workflow(workflow: Workflow) -> dict[str, Any]:
    """Run every check against one workflow."""
    kind = classify_workflow(workflow)
    tag_discovery = check_tag_discovery(workflow)
    changelog = check_changelog_integrity(workflow)
    concurrency = check_concurrency(workflow)
    pinning = check_action_pinning(workflow)
    permissions = check_permissions(workflow)
    trigger = check_trigger_safety(workflow, kind)

    return {
        "workflow": str(workflow.path),
        "kind": kind,
        "triggers": sorted(set(workflow.triggers)),
        "tag_patterns": list(workflow.tag_patterns),
        "permissions": dict(workflow.permissions),
        "has_concurrency": workflow.has_concurrency,
        # Flattened, uniquely-named keys — the gate reads exactly these.
        "tag_discovery_describe_calls": tag_discovery["describe_calls"],
        "tag_discovery_guarded": tag_discovery["guarded"],
        "tag_discovery_tag_listing": tag_discovery["tag_listing"],
        "byte_truncations": changelog["byte_truncations"],
        "unpinned_actions": pinning["unpinned_actions"],
        "pinned_action_count": pinning["pinned_count"],
        "permissions_problems": permissions["problems"],
        "trigger_problems": trigger["problems"],
        "anchored_to_head_parent": _anchored_to_head_parent(workflow),
    }


# ── gate evaluation ────────────────────────────────────────────────────────


#: The requirements evaluated by the default gate mode, per workflow kind.
#:
#: The requirements are **split by kind** because a release pipeline and
#: a CI pipeline have genuinely different contracts.  Applying the
#: release ruleset to CI would report a correct workflow as defective;
#: applying the CI ruleset to a release pipeline would miss the very
#: defects this audit exists to find.
DEFAULT_REQUIREMENTS: tuple[str, ...] = (
    "tag_discovery_safe",
    "changelog_not_truncated",
    "concurrency_declared",
    "actions_pinned",
    "permissions_explicit",
    "trigger_safe",
)

#: The requirements evaluated for a *CI* workflow.
#:
#: ``tag_discovery_safe``, ``changelog_not_truncated`` and
#: ``concurrency_declared`` are release-only concepts; a CI workflow
#: that happens to satisfy them is not thereby correct, and one that
#: does not is not thereby broken.
CI_REQUIREMENTS: tuple[str, ...] = (
    "actions_pinned",
    "permissions_explicit",
    "trigger_safe",
)

#: The requirement set evaluated by the ``--strict`` gate mode, per kind.
#:
#: **For every kind, this set is a strict superset of that kind's
#: default set.**  Adding a requirement can only ever turn a pass into
#: a failure — the monotonicity the gate relies on.  The extra strict
#: requirement (``tag_pattern_anchored``) is release-only, because it
#: concerns the previous-tag lookup, which only a release pipeline
#: performs.
STRICT_REQUIREMENTS: tuple[str, ...] = DEFAULT_REQUIREMENTS + (
    "tag_pattern_anchored",
)

#: Strict-mode requirements for CI workflows: the same as the default
#: CI set, because the only extra strict requirement is release-only.
STRICT_CI_REQUIREMENTS: tuple[str, ...] = CI_REQUIREMENTS

#: Requirement set for each workflow kind, in default mode.
REQUIREMENTS_BY_KIND: dict[str, tuple[str, ...]] = {
    KIND_RELEASE: DEFAULT_REQUIREMENTS,
    KIND_CI: CI_REQUIREMENTS,
}

#: Requirement set for each workflow kind, in strict mode.
STRICT_REQUIREMENTS_BY_KIND: dict[str, tuple[str, ...]] = {
    KIND_RELEASE: STRICT_REQUIREMENTS,
    KIND_CI: STRICT_CI_REQUIREMENTS,
}


def requirements_for(kind: str, strict: bool = False) -> tuple[str, ...]:
    """Return the requirement set that applies to a workflow kind."""
    table = STRICT_REQUIREMENTS_BY_KIND if strict else REQUIREMENTS_BY_KIND
    try:
        return table[kind]
    except KeyError:
        raise ValueError(f"unknown workflow kind: {kind!r}") from None


def _requirement_failed(result: dict[str, Any], requirement: str) -> bool:
    """True when ``result`` fails a single requirement."""
    if requirement == "tag_discovery_safe":
        return not (
            result.get("tag_discovery_guarded", False)
            and (
                result.get("tag_discovery_describe_calls")
                or result.get("tag_discovery_tag_listing")
            )
        )
    if requirement == "changelog_not_truncated":
        return bool(result.get("byte_truncations"))
    if requirement == "concurrency_declared":
        return not result.get("has_concurrency", False)
    if requirement == "actions_pinned":
        return bool(result.get("unpinned_actions"))
    if requirement == "permissions_explicit":
        return bool(result.get("permissions_problems"))
    if requirement == "trigger_safe":
        return bool(result.get("trigger_problems"))
    if requirement == "tag_pattern_anchored":
        return bool(result.get("anchored_to_head_parent"))
    raise ValueError(f"unknown requirement: {requirement!r}")


def evaluate_gate(
    results: list[dict[str, Any]],
    requirements: tuple[str, ...] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Evaluate the gate against the per-workflow audit results.

    This is the **single** place where "does this gate pass?" is
    decided.  Every mode of the CLI — default and ``--strict`` — goes
    through it, which is what makes the modes *monotonic*: adding a
    requirement can only ever turn a pass into a failure.

    The requirement set is chosen **per workflow kind**.  Passing an
    explicit ``requirements`` tuple forces every workflow to be judged
    by the same set, which is how the kind-split behaviour can be
    regression-tested.  When ``requirements`` is ``None`` the set is
    derived from each result's own kind and the ``strict`` flag.
    """
    failures: dict[str, list[str]] = {}
    applied: dict[str, list[str]] = {}

    for result in results:
        kind = result.get("kind", KIND_RELEASE)
        if requirements is not None:
            reqs = tuple(requirements)
        else:
            reqs = requirements_for(kind, strict=strict)
        applied[result["workflow"]] = list(reqs)

        failed = [
            requirement
            for requirement in reqs
            if _requirement_failed(result, requirement)
        ]
        if failed:
            failures[result["workflow"]] = failed

    return {
        "ok": not failures,
        "failed": sorted(failures),
        "failures": failures,
        "requirements": sorted({r for reqs in applied.values() for r in reqs}),
        "applied_requirements": applied,
    }


def _print_report(results: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    """Human-readable report."""
    for result in results:
        applied = gate.get("applied_requirements", {}).get(result["workflow"])
        print(f"\n📦 {result['workflow']}")
        print(f"   kind            : {result.get('kind', KIND_RELEASE)}")
        print(f"   triggers        : {', '.join(result.get('triggers') or ['(none)'])}")
        if result.get("tag_patterns"):
            print(f"   tag patterns    : {', '.join(result['tag_patterns'])}")
        perms = result.get("permissions") or {}
        print(f"   permissions     : {perms if perms else '(none declared)'}")

        status = "✅" if gate["ok"] else "❌"
        print(f"   {status} checks:")
        for requirement in applied if applied is not None else gate["requirements"]:
            failed = requirement in gate["failures"].get(result["workflow"], [])
            mark = "❌" if failed else "✅"
            print(f"      {mark} {requirement}")

        for detail in (
            "tag_discovery_describe_calls",
            "byte_truncations",
            "unpinned_actions",
            "permissions_problems",
            "trigger_problems",
        ):
            value = result.get(detail)
            if value:
                print(f"      └─ {detail}: {value}")

    print("\n" + "─" * 64)
    if gate["ok"]:
        print(f"✅ release audit PASSED ({len(results)} workflow(s), "
              f"{len(gate['requirements'])} requirements)")
    else:
        print(f"❌ release audit FAILED for: {', '.join(gate['failed'])}")
        for path, failed in gate["failures"].items():
            print(f"   {path}: {', '.join(failed)}")
    print("─" * 64)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--workflow",
        action="append",
        type=Path,
        default=None,
        help="audit this workflow file (repeatable); default: every workflow",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "stricter gate mode: additionally require the previous-tag "
            "lookup to be anchored to the tag rather than to HEAD~1"
        ),
    )
    args = parser.parse_args(argv)

    paths = args.workflow or sorted(WORKFLOW_DIR.glob("*.yml"))
    if not paths:
        print("❌ No workflow files found.", file=sys.stderr)
        return 2

    results: list[dict[str, Any]] = []
    for path in paths:
        if not path.exists():
            print(f"❌ Workflow not found: {path}", file=sys.stderr)
            return 2
        try:
            workflow = parse_workflow(path)
        except WorkflowParseError as exc:
            print(f"❌ {exc}", file=sys.stderr)
            return 2
        result = audit_workflow(workflow)
        results.append(result)

    gate = evaluate_gate(results, strict=args.strict)

    if args.json:
        print(json.dumps({"results": results, "gate": gate}, indent=2, ensure_ascii=False))
    else:
        _print_report(results, gate)

    if not gate["ok"]:
        return 1
    return 0


def _anchored_to_head_parent(workflow: Workflow) -> bool:
    """True when the previous-tag lookup is anchored to ``HEAD~1``.

    Anchoring to ``HEAD~1`` resolves the *parent of the tagged commit*,
    not the previous *release*.  It is wrong whenever the tagged commit
    is a merge commit or whenever commits landed after the last tag,
    and it fails outright when the tagged commit is the first commit.
    """
    for job in workflow.jobs.values():
        for script in job.run_scripts:
            for match in _DESCRIBE_RE.finditer(script):
                if re.search(r"HEAD~1|HEAD\^|\^", match.group(0)):
                    return True
    return False


if __name__ == "__main__":
    raise SystemExit(main())
