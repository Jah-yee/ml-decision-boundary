#!/usr/bin/env python3
"""Audit Coverage Audit -- does every CI audit job actually cover what it guards?

The defect class this audit exists for
-------------------------------------

Every other audit in this repository answers a question *about an
artifact*: does this workflow trigger, is this pull request covered,
is the release pipeline safe.  This audit asks a question *about the
audits themselves*: **when audit job X runs, which artifacts does it
actually look at?**

The distinction matters because an audit that runs green while
narrowly scoped produces exactly the wrong signal -- it says "this
area is verified" when the truth is "this area was never looked at".

Concrete instance found in this repository (2026-11-07)
---------------------------------------------------------

``.github/workflows/ci.yml`` contains the job ``release-audit``, which
runs::

    python3 scripts/release_audit.py --workflow .github/workflows/release.yml --strict

The ``--workflow`` argument narrows the audit to a **single file**.
The repository has **two** workflow files, so this job audits
``release.yml`` and never audits ``ci.yml`` -- the workflow that
holds eleven jobs, the pull-request gate, and the token permissions.

Proven defect (measured, not argued)
-------------------------------------

Removing the ``permissions:`` block from ``ci.yml`` -- the exact
defect that the previous round fixed -- leaves **every** audit in
this repository passing green::

    release_audit --workflow .github/workflows/release.yml --strict  exit 0
    ci_trigger_audit.py                                             exit 0
    job_graph_audit.py                                              exit 0

The auditor is capable of catching the defect; the *invocation* never
points it at the file.  So the previous round's fix -- adding
``permissions: contents: read`` to ``ci.yml`` -- has **no guard**: a
future regression lands green.

What this audit checks
----------------------

For every CI job that invokes an audit script, this audit computes
the **coverage set** of that invocation -- the set of workflow files
the invocation will actually examine -- and compares it against the
set the invocation is *supposed* to cover.

Two checks:

1. ``coverage_narrowed``
   The invocation names explicit paths (via ``--workflow``) and those
   paths are a **strict subset** of the workflow files that exist.
   The audit script supports a default discovery glob, so narrowing
   is always a narrowing of coverage.

2. ``workflow_uncovered``
   A workflow file that no audit invocation covers at all.

Both are defects of the *coverage* kind, independent of whether the
audited artifact is currently correct.

Design notes
------------

* Pure standard library.  No PyYAML: this repository parses workflow
  files with a small hand-written YAML subset reader, and this audit
  follows the same convention.
* Hermetic.  It reads the repository's own files and nothing else --
  no network, no git, no GitHub API.
* The strict mode's requirement set is a **strict superset** of the
  default mode's, and both modes decide through the single
  ``evaluate_gate()`` function, so ``--strict`` can only ever turn a
  pass into a failure.

Usage
-----

    python3 scripts/audit_coverage_audit.py            # default gate
    python3 scripts/audit_coverage_audit.py --strict    # strict gate
    python3 scripts/audit_coverage_audit.py --json     # machine-readable
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parent.parent
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
SCRIPTS_DIR = REPO_ROOT / "scripts"

#: Requirement checked in default mode.
DEFAULT_REQUIREMENT = "coverage_complete"
#: Additional requirement checked in ``--strict`` mode.
STRICT_REQUIREMENT = "no_narrowed_invocations"


class AuditCoverageError(RuntimeError):
    """Raised when a workflow file cannot be parsed."""


# ── YAML subset reader ─────────────────────────────────────────────────────

_JOB_KEY_RE = re.compile(r"^  (?P<name>[A-Za-z0-9_.-]+):\s*$")
# A step's ``run:`` key.  Two shapes occur:
#   ``- run: <cmd>``      -- the command is a list item at indent 6;
#   ``  run: <cmd>``      -- the command follows a ``- name:`` at indent 8.
# The regex accepts both, and the caller rejects a ``run:`` that is
# not inside a ``steps:`` block.
_RUN_KEY_RE = re.compile(r"^\s*(?:-\s+)?run:\s*(?P<rest>.*)$")
_STEP_ENTRY_RE = re.compile(r"^      - (?P<rest>.*)$")
_STEPS_KEY_RE = re.compile(r"^    steps:\s*$")
_COMMENT_RE = re.compile(r"\s+#.*$")


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

    def to_dict(self) -> dict[str, Any]:
        return {"name": self.name, "run": self.run}


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": str(self.path),
            "jobs": {k: v.to_dict() for k, v in self.jobs.items()},
        }


def parse_workflow(path: Path) -> Workflow:
    """Parse the ``jobs:`` block of a workflow file.

    The reader is deliberately minimal: it understands a ``jobs:``
    mapping whose entries are two-space indented job names, each with
    a four-space indented ``steps:`` list of ``- run:`` entries.
    That is exactly the shape needed to find the audit invocations.

    **Block scalars.**  A step may be written as ``run: |`` followed
    by an indented block of shell commands -- which is how every
    multi-line CI step in this repository is written.  Such a block
    is folded into the step's command with newlines, because an audit
    invocation can sit on any line of the block.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise AuditCoverageError(f"cannot read {path}: {exc}") from exc

    lines = text.splitlines()
    workflow = Workflow(path=path)

    in_jobs = False
    current_job: Job | None = None
    in_steps = False
    # Block-scalar state: the steps currently collecting a ``run: |``
    # body, and the indent of that body.
    block_steps: list[Step] = []
    in_block = False
    block_indent: int | None = None
    block_parent_indent = 0

    for raw in lines:
        line = _strip_comment(raw)
        if not line.strip():
            continue

        indent = len(line) - len(line.lstrip(" "))

        if indent == 0:
            in_jobs = line.startswith("jobs:")
            current_job = None
            in_steps = False
            continue

        if not in_jobs:
            continue

        job_match = _JOB_KEY_RE.match(line)
        if job_match and indent == 2:
            current_job = Job(name=job_match.group("name"))
            workflow.jobs[current_job.name] = current_job
            in_steps = False
            continue

        if indent == 4 and line.strip() == "steps:":
            in_steps = True
            continue

        if in_block and current_job is not None and block_steps:
            # The block body is indented deeper than the ``run:`` key
            # that opened it.  A line at or below that level ends the
            # block.  This branch must be tested *before* the plain
            # step branch: a body line has indent >= 6 too, and the
            # plain branch would otherwise swallow it.
            if block_indent is None:
                if indent > block_parent_indent:
                    block_indent = indent
                    block_steps[-1].run = (
                        block_steps[-1].run + "\n" + line if block_steps[-1].run else line
                    )
                    continue
            elif indent >= block_indent:
                block_steps[-1].run = (
                    block_steps[-1].run + "\n" + line if block_steps[-1].run else line
                )
                continue
            # Dedent ends the block scalar.
            in_block = False
            block_steps.clear()
            block_indent = None

        if in_steps and indent >= 6:
            run_match = _RUN_KEY_RE.match(line)
            if run_match and current_job is not None:
                rest = run_match.group("rest").strip()
                if rest in ("|", ">", "|-", ">-"):
                    # Block scalar: the command continues on the
                    # following, more-indented lines.
                    current_job.steps.append(Step(run="", name="__block__"))
                    block_steps.append(current_job.steps[-1])
                    in_block = True
                    block_indent = None
                    block_parent_indent = indent
                else:
                    current_job.steps.append(Step(run=rest))
            continue

    return workflow


# ── audit invocation discovery ─────────────────────────────────────────────

#: Matches ``python3 scripts/<name>.py`` inside a run command.
_AUDIT_SCRIPT_RE = re.compile(r"scripts/(?P<script>[A-Za-z0-9_]+\.py)")

#: Matches a ``--workflow <path>`` narrowing argument.
_WORKFLOW_ARG_RE = re.compile(r"--workflow\s+(?P<path>[^\s'\"]+)")

#: The audit scripts this audit knows how to reason about.  Each entry
#: says whether the script supports a default discovery glob (so that
#: naming paths is a *narrowing* of coverage).
#:
#: Only scripts that actually examine **workflow files** belong here.
#: ``pr_coverage_audit.py`` is deliberately absent: it audits *pull
#: requests* against a workflow definition, it does not audit the
#: workflow file itself, so a ``--workflow`` narrowing would not mean
#: anything for it.  Listing it would produce a false positive.
KNOWN_AUDITS: dict[str, dict[str, Any]] = {
    "ci_trigger_audit.py": {"supports_glob": True},
    "job_graph_audit.py": {"supports_glob": True},
    "release_audit.py": {"supports_glob": True},
}


@dataclass
class Invocation:
    """One audit-script invocation found in a CI job."""

    script: str
    job: str
    workflow_file: str
    command: str
    explicit_paths: list[str] = field(default_factory=list)

    @property
    def is_narrowed(self) -> bool:
        return bool(self.explicit_paths)

    def to_dict(self) -> dict[str, Any]:
        return {
            "script": self.script,
            "job": self.job,
            "workflow_file": self.workflow_file,
            "command": self.command,
            "explicit_paths": list(self.explicit_paths),
            "is_narrowed": self.is_narrowed,
        }


def discover_invocations(workflow: Workflow) -> list[Invocation]:
    """Find every audit-script invocation in a workflow's jobs.

    A step is an audit invocation when its ``run:`` command mentions
    ``scripts/<audit>.py``.  The command may be a multi-line shell
    block; every ``scripts/<audit>.py`` mention in it counts.
    """
    invocations: list[Invocation] = []
    for job in workflow.jobs.values():
        for run in job.run_scripts:
            for match in _AUDIT_SCRIPT_RE.finditer(run):
                script = match.group("script")
                if script not in KNOWN_AUDITS:
                    continue
                paths = [m.group("path") for m in _WORKFLOW_ARG_RE.finditer(run)]
                invocations.append(
                    Invocation(
                        script=script,
                        job=job.name,
                        workflow_file=workflow.path.name,
                        command=run.strip(),
                        explicit_paths=paths,
                    )
                )
    return invocations


def resolve_covered(invocation: Invocation, workflow_files: list[str]) -> set[str]:
    """Return the workflow filenames an invocation actually examines.

    An invocation with no ``--workflow`` argument covers every
    workflow file (the audit script's own default discovery).  An
    invocation with explicit paths covers exactly those paths.
    """
    if not invocation.explicit_paths:
        return set(workflow_files)
    covered: set[str] = set()
    for raw in invocation.explicit_paths:
        name = Path(raw).name
        covered.add(name)
    return covered


# ── checks ─────────────────────────────────────────────────────────────────


def check_coverage(
    invocations: list[Invocation],
    workflow_files: list[str],
) -> dict[str, Any]:
    """Check that audit invocations cover the workflow files they guard.

    Two defects are detected:

    ``coverage_narrowed``
        An invocation names explicit workflow paths and those paths do
        not cover every workflow file in the repository.  Because the
        audit scripts support a default discovery glob, naming paths
        always reduces coverage.

    ``workflow_uncovered``
        A workflow file that no audit invocation covers at all.
    """
    problems: list[dict[str, Any]] = []
    per_invocation: list[dict[str, Any]] = []

    union_covered: set[str] = set()
    for invocation in invocations:
        covered = resolve_covered(invocation, workflow_files)
        union_covered |= covered
        missing = sorted(set(workflow_files) - covered)
        entry = invocation.to_dict()
        entry["covers"] = sorted(covered)
        entry["misses"] = missing
        per_invocation.append(entry)

        if invocation.is_narrowed and missing:
            problems.append(
                {
                    "check": "coverage_narrowed",
                    "script": invocation.script,
                    "job": invocation.job,
                    "workflow_file": invocation.workflow_file,
                    "command": invocation.command,
                    "covers": sorted(covered),
                    "misses": missing,
                    "detail": (
                        f"{invocation.script} in job '{invocation.job}' "
                        f"audits only {sorted(covered)}; it never examines "
                        f"{missing}. The script's default discovery glob "
                        f"would cover all {len(workflow_files)} workflow(s)."
                    ),
                }
            )

    for name in sorted(set(workflow_files) - union_covered):
        problems.append(
            {
                "check": "workflow_uncovered",
                "script": "",
                "job": "",
                "workflow_file": name,
                "command": "",
                "covers": [],
                "misses": [name],
                "detail": (
                    f"workflow '{name}' is not examined by any audit "
                    f"invocation in the CI workflow."
                ),
            }
        )

    return {
        "ok": not problems,
        "problems": problems,
        "invocations": per_invocation,
        "workflow_files": sorted(workflow_files),
        "covered": sorted(union_covered),
        "uncovered": sorted(set(workflow_files) - union_covered),
    }


# ── gate evaluation ────────────────────────────────────────────────────────

DEFAULT_REQUIREMENTS: tuple[str, ...] = (DEFAULT_REQUIREMENT,)
STRICT_REQUIREMENTS: tuple[str, ...] = (
    DEFAULT_REQUIREMENT,
    STRICT_REQUIREMENT,
)


def _requirement_failed(result: dict[str, Any], requirement: str) -> bool:
    """True when ``result`` fails a single requirement."""
    problems = result.get("problems", [])
    if requirement == DEFAULT_REQUIREMENT:
        # The default gate fails if *any* coverage problem exists.
        return bool(problems)
    if requirement == STRICT_REQUIREMENT:
        # The strict gate additionally forbids a narrowed invocation --
        # even when the narrowing happens to cover every workflow
        # file.  The narrowing must be read off the *invocations*,
        # not off the problem list: a narrowing that covers
        # everything is not a coverage problem, but it is still a
        # narrowing, and the strict mode exists to forbid the habit.
        for invocation in result.get("invocations", []):
            if invocation.get("is_narrowed"):
                return True
        return False
    raise ValueError(f"unknown requirement: {requirement!r}")


def evaluate_gate(
    result: dict[str, Any],
    requirements: tuple[str, ...] | None = None,
    strict: bool = False,
) -> dict[str, Any]:
    """Evaluate the gate against the coverage audit result.

    This is the **single** place where "does this gate pass?" is
    decided.  Every mode of the CLI -- default and ``--strict`` --
    goes through it, which is what makes the modes *monotonic*:
    adding a requirement can only ever turn a pass into a failure.
    """
    if requirements is None:
        requirements = STRICT_REQUIREMENTS if strict else DEFAULT_REQUIREMENTS

    failed = [
        requirement
        for requirement in requirements
        if _requirement_failed(result, requirement)
    ]

    return {
        "ok": not failed,
        "mode": "strict" if strict else "default",
        "requirements": list(requirements),
        "failed": failed,
        "problems": result.get("problems", []),
    }


# ── driver ─────────────────────────────────────────────────────────────────


def audit_repo(
    workflow_dir: Path = WORKFLOW_DIR,
    ci_workflow: Path | None = None,
) -> dict[str, Any]:
    """Run the coverage audit over the repository's workflows.

    ``ci_workflow`` names the workflow whose jobs are examined for
    audit invocations.  It defaults to ``ci.yml`` inside
    ``workflow_dir``.
    """
    if not workflow_dir.is_dir():
        raise AuditCoverageError(f"workflow directory not found: {workflow_dir}")

    workflow_files = sorted(p.name for p in workflow_dir.glob("*.yml"))

    if ci_workflow is None:
        ci_workflow = workflow_dir / "ci.yml"
    if not ci_workflow.exists():
        raise AuditCoverageError(f"CI workflow not found: {ci_workflow}")

    parsed = parse_workflow(ci_workflow)
    invocations = discover_invocations(parsed)
    result = check_coverage(invocations, workflow_files)
    result["ci_workflow"] = str(ci_workflow)
    return result


def _print_report(result: dict[str, Any], gate: dict[str, Any]) -> None:
    print(f"📦 {result['ci_workflow']}")
    print(f"   workflows      : {result['workflow_files']}")
    print(f"   invocations    : {len(result['invocations'])}")
    print()

    for entry in result["invocations"]:
        marker = "⚠️ " if entry["is_narrowed"] else "   "
        print(f"   {marker}{entry['script']}  (job: {entry['job']})")
        print(f"      covers : {entry['covers']}")
        if entry["misses"]:
            print(f"      misses : {entry['misses']}")

    print()
    if gate["ok"]:
        print("✅ checks:")
        for requirement in gate["requirements"]:
            print(f"   ✅ {requirement}")
        print()
        print(
            f"✅ audit coverage audit PASSED "
            f"({len(result['workflow_files'])} workflow(s))"
        )
        return

    print("❌ checks:")
    for requirement in gate["requirements"]:
        mark = "❌" if requirement in gate["failed"] else "✅"
        print(f"   {mark} {requirement}")
    print()
    for problem in gate["problems"]:
        print(f"❌ {problem['check']}: {problem['detail']}")
    print()
    print("❌ audit coverage audit FAILED")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--workflow-dir",
        type=Path,
        default=WORKFLOW_DIR,
        help="directory holding the workflow files to cover",
    )
    parser.add_argument(
        "--ci-workflow",
        type=Path,
        default=None,
        help="workflow whose jobs are examined for audit invocations",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="stricter gate mode: additionally forbid narrowed invocations",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    try:
        result = audit_repo(
            workflow_dir=args.workflow_dir,
            ci_workflow=args.ci_workflow,
        )
    except AuditCoverageError as exc:
        print(f"❌ {exc}", file=sys.stderr)
        return 2

    gate = evaluate_gate(result, strict=args.strict)

    if args.json:
        payload = {**result, "gate": gate}
        print(json.dumps(payload, indent=2, sort_keys=True))
        return 0 if gate["ok"] else 1

    _print_report(result, gate)
    return 0 if gate["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
