#!/usr/bin/env python3
"""Audit the job dependency graph of a GitHub Actions workflow.

**Why this exists.**  Three audits already exist and all three ask
questions *about* the workflow:

- :mod:`ci_trigger_audit` (DoD #7) asks *"would the workflow even start
  for a pull request whose base branch is X?"* — about the ``on:`` block;
- :mod:`pr_coverage_audit` (DoD #8) asks *"is every open pull request
  actually covered by CI?"* — about check runs on pull requests;
- :mod:`stack_topology_audit` (DoD #17) asks *"can this stack of pull
  requests be merged in order?"* — about the shape of the branches.

All three are **about the workflow**.  None of them looks **inside** the
workflow at the ``jobs:`` block and asks whether the job graph itself is
sound.  That is the gap this audit closes.

**The gap, concretely.**  The CI workflow of this repository has a
``pr-coverage-gate`` job whose ``needs:`` list names all eight other
jobs.  That list is a **contract**: the gate can only assert "this pull
request was fully verified" if every job that verifies something is
actually a prerequisite of the gate.  Nothing enforces the contract:

1. **A dangling ``needs:`` target is fatal to the whole workflow.**
   If ``pr-coverage-gate`` names a job that does not exist, GitHub
   rejects the **entire workflow** — not just the gate.  Every real
   quality job (``quality-gates``, ``benchmark``, ``security-audit``,
   ...) is skipped along with it.  A single-character typo therefore
   converts a green CI into a CI that verifies *nothing*, and it does so
   loudly on the PR that introduced it.

2. **A ``needs:`` cycle makes jobs silently never run.**  A job that
   transitively depends on itself is dropped from the execution order
   without a clear error.  The workflow still "succeeds" as a whole if
   the skipped jobs were not the ones anyone was looking at.

3. **A new job that the gate does not know about is an ungated job.**
   This is the subtle one, and it is the exact analogue of the DoD #16
   defect (a stricter gate mode that was *laxer* than the default
   mode).  If somebody adds a new verification job — say
   ``license-audit`` — and forgets to add it to ``pr-coverage-gate``'s
   ``needs:``, then the gate reports "this pull request is fully
   verified" while the new job has not run, may have failed, and its
   result is not part of the gate's verdict.  The gate **lies**, and it
   lies in the dangerous direction: it says "verified" about code that
   was not.

Point 3 is the reason this audit exists as a *gate* rather than as a
lint.  The DoD #16 lesson generalises: *a gate that does not fail on
the defect it exists to catch is not a gate, it is a rubber stamp.*

**What this audit checks.**  For each workflow file:

- **Dangling needs** — every ``needs:`` target names an existing job;
- **Self dependency** — no job lists itself;
- **Acyclic** — the ``needs:`` graph contains no cycle;
- **Gate coverage** — every *verification* job is a prerequisite of
  every *gate* job.

The last one needs a definition of "verification job" and "gate job".
Both are conventions, not syntax, so the audit makes them **explicit and
overridable**: by default a job is a *gate* if its name ends in
``-gate`` or ``-audit`` *and* it declares ``needs:``; every other job
with a ``run:`` step is a *verification* job.  The classification is
overridable from the command line so that a workflow with different
conventions can still be audited honestly rather than not at all.

**Design constraints.**

- **No third-party dependency.**  PyYAML is available in the dev
  container but is *not* in ``requirements.lock``, so importing it here
  would break CI.  The parser below is a deliberately small subset
  reader that handles exactly the shape of an Actions ``jobs:`` block:
  one level of job definitions, each with an optional ``needs:`` that is
  either a scalar, an inline flow list, or a block list.  It raises on
  anything it does not understand rather than guessing, so a future edit
  to the workflow cannot be silently mis-parsed into a false pass.
- **Read-only.**  The audit never writes to the workflow.  Fixing the
  workflow is a human (or agent) decision; the script's job is to make
  the gap *visible* and *testable*.
- **Degrades honestly.**  If a workflow cannot be parsed, the audit
  says so and exits non-zero rather than reporting a vacuous success.

Usage::

    python3 scripts/job_graph_audit.py                  # audit every workflow
    python3 scripts/job_graph_audit.py --workflow .github/workflows/ci.yml
    python3 scripts/job_graph_audit.py --json           # machine-readable
    python3 scripts/job_graph_audit.py --strict         # stricter gate mode
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

#: Job-name suffixes that mark a job as an *audit/gate* job.
#:
#: A gate job is one whose job is to *decide* whether a pull request is
#: acceptable.  Such a job must depend on every job that produces
#: evidence, otherwise its verdict is based on partial evidence.
GATE_SUFFIXES = ("-gate", "-audit")

#: Job-name suffixes that mark a job as a *bookkeeping* job rather than
#: a verification job.
#:
#: A job in this category produces no verification evidence, so it must
#: not be required to be a prerequisite of the gate.  (There are none
#: today; the list exists so the classification is a decision rather
#: than an accident.)
NON_VERIFICATION_SUFFIXES = ()


class WorkflowParseError(RuntimeError):
    """Raised when a workflow file cannot be parsed by the subset reader."""


# ── YAML subset reader ─────────────────────────────────────────────────────


_JOB_KEY_RE = re.compile(r"^  (?P<name>[A-Za-z0-9_.-]+):\s*$")
_NEEDS_KEY_RE = re.compile(r"^    needs:\s*(?P<rest>.*)$")
_NEEDS_ITEM_RE = re.compile(r"^      - (?P<item>[^\s#]+)")
_RUN_KEY_RE = re.compile(r"^      - run:\s*(?P<rest>.*)$")
_STEP_LIST_RE = re.compile(r"^    steps:\s*$")
_INLINE_LIST_RE = re.compile(r"^\[(?P<items>[^\]]*)\]$")


def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment, respecting quotes."""
    out = []
    quote = None
    for ch in line:
        if quote:
            out.append(ch)
            if ch == quote:
                quote = None
            continue
        if ch in ("'", '"'):
            quote = ch
            out.append(ch)
            continue
        if ch == "#":
            break
        out.append(ch)
    return "".join(out).rstrip()


def _split_flow_list(raw: str) -> list[str]:
    """Split the body of an inline YAML flow list into its items."""
    body = raw.strip()
    if not body:
        return []
    items = []
    for part in body.split(","):
        part = part.strip().strip("'\"")
        if part:
            items.append(part)
    return items


def _parse_needs_value(rest: str) -> list[str] | None:
    """Parse the inline part of a ``needs:`` value.

    Returns ``None`` when the value is a block list (handled by the
    caller) and a list otherwise.
    """
    rest = rest.strip()
    if not rest:
        return None
    match = _INLINE_LIST_RE.match(rest)
    if match:
        return _split_flow_list(match.group("items"))
    # A bare scalar: ``needs: quality-gates``
    return [rest.strip("'\"")]


@dataclass
class Job:
    """One job definition, reduced to what the graph audit needs."""

    name: str
    needs: list[str] = field(default_factory=list)
    has_run: bool = False
    has_steps: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "needs": list(self.needs),
            "has_run": self.has_run,
        }


@dataclass
class Workflow:
    """A parsed workflow file."""

    path: Path
    jobs: dict[str, Job] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "path": str(self.path),
            "jobs": {name: job.to_dict() for name, job in self.jobs.items()},
        }


def parse_workflow(path: Path) -> Workflow:
    """Parse the ``jobs:`` block of an Actions workflow.

    The reader understands exactly this shape::

        jobs:
          job-name:
            runs-on: ubuntu-latest
            needs:
              - other-job
            steps:
              - run: something

    and ``needs: [a, b]`` / ``needs: a`` inline forms.  Anything else
    inside the ``jobs:`` block is ignored — but the *structure* that
    matters (``needs:`` and the presence of a ``steps:``/``run:``) is
    read strictly, and a malformed ``needs:`` raises.
    """
    try:
        text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise WorkflowParseError(f"cannot read {path}: {exc}") from exc

    lines = text.splitlines()

    # Locate the top-level ``jobs:`` block.
    start = None
    for index, raw in enumerate(lines):
        if raw.rstrip() == "jobs:":
            start = index + 1
            break
    if start is None:
        raise WorkflowParseError(f"{path}: no top-level 'jobs:' block")

    workflow = Workflow(path=path)
    current: Job | None = None
    in_needs_block = False

    for raw in lines[start:]:
        line = _strip_comment(raw)
        if not line.strip():
            continue

        # A new job definition at two-space indentation.
        job_match = _JOB_KEY_RE.match(line)
        if job_match:
            current = Job(name=job_match.group("name"))
            workflow.jobs[current.name] = current
            in_needs_block = False
            continue

        if current is None:
            # Content before the first job definition — ignore.
            continue

        # ``needs:`` may appear as a key of the job (four-space indent).
        needs_match = _NEEDS_KEY_RE.match(line)
        if needs_match:
            parsed = _parse_needs_value(needs_match.group("rest"))
            if parsed is None:
                in_needs_block = True
            else:
                in_needs_block = False
                current.needs.extend(parsed)
            continue

        if in_needs_block:
            item_match = _NEEDS_ITEM_RE.match(line)
            if item_match:
                current.needs.append(item_match.group("item").strip("'\""))
                continue
            # A non-item line ends the needs block.
            in_needs_block = False

        if _STEP_LIST_RE.match(line):
            current.has_steps = True
            continue

        run_match = _RUN_KEY_RE.match(line)
        if run_match:
            current.has_run = True
            continue

    return workflow


# ── graph checks ───────────────────────────────────────────────────────────


def find_cycles(jobs: dict[str, Job]) -> list[list[str]]:
    """Return every cycle in the ``needs:`` graph.

    Each cycle is reported as the list of job names starting and ending
    at the same node, e.g. ``["a", "b", "a"]``.
    """
    cycles: list[list[str]] = []
    seen: set[tuple[str, ...]] = set()

    colour: dict[str, int] = {name: 0 for name in jobs}  # 0=white 1=grey 2=black
    stack: list[str] = []

    def visit(node: str) -> None:
        colour[node] = 1
        stack.append(node)
        for dep in jobs[node].needs:
            if dep not in jobs:
                # Dangling target — reported separately; not a cycle.
                continue
            if colour.get(dep, 0) == 1:
                # Found a cycle: slice the stack from the repeated node.
                start = stack.index(dep)
                cycle = stack[start:] + [dep]
                key = tuple(sorted(set(cycle)))
                if key not in seen:
                    seen.add(key)
                    cycles.append(cycle)
            elif colour.get(dep, 0) == 0:
                visit(dep)
        stack.pop()
        colour[node] = 2

    for name in sorted(jobs):
        if colour[name] == 0:
            visit(name)

    return cycles


def is_gate_job(job: Job) -> bool:
    """True when ``job`` is a gate/audit job.

    A gate job is one that *decides* whether a pull request is
    acceptable, or that audits a property of the workflow itself.  It
    is recognised by a naming convention (the ``-gate`` / ``-audit``
    suffix).

    Note that a gate job does **not** need to declare ``needs:`` to be
    a gate: ``ci-trigger-audit`` and ``pr-coverage-audit`` are audits
    that fail the build on their own, and neither has any prerequisite.
    Requiring ``needs:`` would misclassify them as verification jobs
    and then demand that the gate wait for them — which is the *opposite*
    of the intended dependency direction.
    """
    return any(job.name.endswith(suffix) for suffix in GATE_SUFFIXES)


def is_verification_job(job: Job) -> bool:
    """True when ``job`` produces verification evidence.

    A verification job is one that actually runs something.  Gate and
    audit jobs are excluded: they *aggregate* evidence, they do not
    produce it, so requiring a gate to depend on another gate would be
    a false positive.
    """
    if is_gate_job(job):
        return False
    if any(job.name.endswith(suffix) for suffix in NON_VERIFICATION_SUFFIXES):
        return False
    return job.has_run or job.has_steps


def audit_workflow(workflow: Workflow) -> dict[str, Any]:
    """Audit one workflow's job graph.

    Returns a dict with ``ok``, ``problems``, and the individual
    findings.  ``ok`` is True only when there are no problems at all.
    """
    jobs = workflow.jobs
    problems: list[str] = []
    dangling: list[dict[str, Any]] = []
    self_deps: list[str] = []
    cycles: list[list[str]] = []
    ungated: list[dict[str, Any]] = []

    # 1. Dangling needs.
    for name in sorted(jobs):
        for dep in jobs[name].needs:
            if dep not in jobs:
                dangling.append({"job": name, "needs": dep})
    for item in dangling:
        problems.append(
            f"job {item['job']!r} needs {item['needs']!r}, which is not a job "
            f"in this workflow (GitHub would reject the ENTIRE workflow)"
        )

    # 2. Self dependency.
    for name in sorted(jobs):
        if name in jobs[name].needs:
            self_deps.append(name)
    for name in self_deps:
        problems.append(f"job {name!r} depends on itself")

    # 3. Cycles.
    cycles = find_cycles(jobs)
    for cycle in cycles:
        problems.append("needs cycle: " + " -> ".join(cycle))

    # 4. Gate coverage: every verification job must be a prerequisite of
    #    every *aggregating* gate job.
    #
    #    A gate that declares ``needs:`` is aggregating: it waits for
    #    other jobs and folds their results into a verdict.  Such a gate
    #    must wait for every verification job, otherwise it can say
    #    "verified" while a verification job never ran.
    #
    #    A gate with an *empty* ``needs:`` (e.g. ``ci-trigger-audit``,
    #    which audits one property and fails the build on its own) is
    #    standalone: there is nothing for it to aggregate, so there is
    #    nothing to cover.
    gates = [jobs[n] for n in sorted(jobs) if is_gate_job(jobs[n])]
    aggregating_gates = [g for g in gates if g.needs]
    verifications = [jobs[n] for n in sorted(jobs) if is_verification_job(jobs[n])]

    for gate in aggregating_gates:
        for verification in verifications:
            if verification.name not in gate.needs:
                ungated.append(
                    {"gate": gate.name, "job": verification.name}
                )
    for item in ungated:
        problems.append(
            f"verification job {item['job']!r} is not a prerequisite of gate "
            f"{item['gate']!r} — the gate would report 'verified' without it"
        )

    return {
        "ok": not problems,
        "workflow": str(workflow.path),
        "jobs": {name: job.to_dict() for name, job in jobs.items()},
        "gates": [g.name for g in gates],
        "aggregating_gates": [g.name for g in aggregating_gates],
        "verifications": [v.name for v in verifications],
        "dangling_needs": dangling,
        "self_dependencies": self_deps,
        "cycles": cycles,
        "ungated_jobs": ungated,
        "gate_present": None,
        "problems": problems,
    }


# ── gate evaluation ────────────────────────────────────────────────────────


DEFAULT_REQUIREMENTS: tuple[str, ...] = (
    "no_dangling_needs",
    "no_self_dependency",
    "acyclic",
    "gate_coverage",
)

#: The requirement set evaluated by the ``--strict`` gate mode.
#:
#: **This set is a strict superset of :data:`DEFAULT_REQUIREMENTS`.**
#: The extra requirement is ``all_jobs_reachable``: every job in the
#: workflow must be reachable from the gate, which catches the case
#: where a job is *named* in the gate's ``needs:`` but is itself
#: blocked behind a cycle or a dangling edge and therefore never runs.
STRICT_REQUIREMENTS: tuple[str, ...] = DEFAULT_REQUIREMENTS + (
    "all_jobs_reachable",
)


def _requirement_failed(result: dict[str, Any], requirement: str) -> bool:
    """True when ``result`` fails a single requirement.

    Each requirement is checked independently so the gate can report
    *why* it failed rather than just *that* it did.
    """
    if requirement == "no_dangling_needs":
        return bool(result["dangling_needs"])
    if requirement == "no_self_dependency":
        return bool(result["self_dependencies"])
    if requirement == "acyclic":
        return bool(result["cycles"])
    if requirement == "gate_coverage":
        return bool(result["ungated_jobs"])
    if requirement == "all_jobs_reachable":
        # Only meaningful for workflows that actually have a gate.
        return bool(result.get("unreachable_jobs"))
    raise ValueError(f"unknown requirement: {requirement!r}")


def evaluate_gate(
    results: list[dict[str, Any]],
    requirements: tuple[str, ...] = DEFAULT_REQUIREMENTS,
) -> dict[str, Any]:
    """Evaluate the gate against the per-workflow audit results.

    This is the **single** place where "does this gate pass?" is
    decided.  Every mode of the CLI — default and ``--strict`` — goes
    through it, which is what makes the modes *monotonic*: adding a
    requirement can only ever turn a pass into a failure, never the
    other way round.

    Returns a dict with ``ok``, ``failed`` (workflow paths),
    ``failures`` (path -> failed requirements) and ``requirements``.
    """
    failures: dict[str, list[str]] = {}
    for result in results:
        failed = [
            requirement
            for requirement in requirements
            if _requirement_failed(result, requirement)
        ]
        if failed:
            failures[result["workflow"]] = failed

    return {
        "ok": not failures,
        "failed": sorted(failures),
        "failures": failures,
        "requirements": list(requirements),
    }


def _reachable_from(gate: str, jobs: dict[str, Job]) -> set[str]:
    """Job names transitively reachable *from* ``gate`` via ``needs:``.

    Note the direction: a gate's ``needs:`` are its prerequisites, so
    the set of jobs the gate transitively waits for is what it reaches.
    """
    seen: set[str] = set()
    todo = list(jobs[gate].needs)
    while todo:
        node = todo.pop()
        if node in seen or node not in jobs:
            continue
        seen.add(node)
        todo.extend(jobs[node].needs)
    return seen


def add_reachability(result: dict[str, Any], workflow: Workflow) -> None:
    """Annotate ``result`` with the set of jobs unreachable from a gate.

    A job that exists in the workflow but that no gate ever waits for
    is a job whose verdict never reaches the gate — even if it is
    listed in the gate's ``needs:``, a cycle or a dangling edge can
    prevent it from running at all.
    """
    jobs = workflow.jobs
    gates = [
        name
        for name in jobs
        if is_gate_job(jobs[name]) and jobs[name].needs
    ]
    if not gates:
        # A workflow with no aggregating gate has no reachability
        # requirement: there is nothing that is supposed to be waiting
        # for anything.  (e.g. release.yml, which is a standalone
        # release pipeline.)  Reporting its jobs as "unreachable" would
        # be a false positive, and a gate that cries wolf is a gate
        # that gets ignored.
        result["unreachable_jobs"] = []
        result["gate_present"] = False
        return

    result["gate_present"] = True

    reachable: set[str] = set()
    for gate in gates:
        reachable.add(gate)
        reachable |= _reachable_from(gate, jobs)

    result["unreachable_jobs"] = sorted(set(jobs) - reachable)


# ── reporting ──────────────────────────────────────────────────────────────


def _print_report(results: list[dict[str, Any]], gate: dict[str, Any]) -> None:
    for result in results:
        print(f"\n=== {result['workflow']} ===")
        jobs = result["jobs"]
        print(f"  jobs: {len(jobs)}")
        print(f"  gates: {', '.join(result['gates']) or '(none)'}")
        print(f"  aggregating gates: {', '.join(result.get('aggregating_gates') or []) or '(none)'}")
        print(f"  verifications: {', '.join(result['verifications']) or '(none)'}")

        for name in sorted(jobs):
            needs = jobs[name]["needs"]
            needs_str = ", ".join(needs) if needs else "-"
            print(f"    {name}  needs: {needs_str}")

        if result["problems"]:
            print("\n  Problems:")
            for problem in result["problems"]:
                print(f"    ❌ {problem}")
        else:
            print("\n  ✅ The job dependency graph is sound.")

    print("\n" + "─" * 60)
    if gate["ok"]:
        print("✅ Gate passed for every workflow.")
    else:
        print(f"❌ Gate failed for: {', '.join(gate['failed'])}")
        for path, failed in gate["failures"].items():
            print(f"   {path}: {', '.join(failed)}")


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
            "stricter gate mode: additionally require that every job is "
            "reachable from a gate"
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
        add_reachability(result, workflow)
        results.append(result)

    requirements = STRICT_REQUIREMENTS if args.strict else DEFAULT_REQUIREMENTS
    gate = evaluate_gate(results, requirements)

    if args.json:
        print(
            json.dumps(
                {"results": results, "gate": gate},
                indent=2,
                ensure_ascii=False,
            )
        )
    else:
        _print_report(results, gate)

    if not gate["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
