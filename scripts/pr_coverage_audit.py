#!/usr/bin/env python3
"""Audit whether each open pull request is actually covered by CI.

**Why this exists.**  ``scripts/ci_trigger_audit.py`` audits the trigger
block of *a workflow file on the current working tree*.  That answers the
question *"if I were to open a pull request with base X, would CI run?"*.

It does **not** answer the question GitHub actually answers when it
decides whether to start a workflow for a pull request that already
exists:

> GitHub reads the workflow definitions **from the pull request's head
> branch** — not from the base branch, and not from the default branch.

That distinction turns out to matter a great deal for *stacked* pull
requests.  This repository uses a stacked layout:

```
master
  └── feat/v13-provenance-provenance   (PR #61)
        └── feat/v13-replay-provenance  (PR #62)
              └── feat/v13-replay-integrity-guard  (PR #63)
                    └── feat/v13-ci-trigger-coverage (PR #66)
```

Suppose PR #66 removes the ``branches: [master]`` filter from
``.github/workflows/ci.yml``.  PR #66 now gets full CI — but **PR #63
still does not**, because PR #63's head branch
(``feat/v13-replay-integrity-guard``) still carries the *old* filtered
workflow.  GitHub will not "preview" PR #66's file changes onto PR #63.

The result is a **merge-order deadlock**:

* to give PR #63 a green CI, you must first merge the fix into PR #63's
  branch — but the fix lives in PR #66, whose base *is* PR #63;
* so PR #63's code (the replay integrity guard and 51 new tests) can sit
  unverified for as long as nobody thinks to merge by hand.

The failure is invisible.  A *failing* check is red, and a *running*
check is grey; but a pull request that will **never** be checked shows an
**empty** check list, which reads like "not started yet".

**What this script does.**  For each open pull request it answers three
questions:

1. *Does the workflow on this pull request's head branch subscribe to
   ``pull_request`` at all?*
2. *Does that workflow's ``pull_request`` trigger cover this pull
   request's own base branch?*
3. *What is the actual observed check state?* (``statusCheckRollup``)

Only when all three line up — the workflow subscribes, the filter covers
the base, and checks actually exist — is the pull request *verified*.

**Design constraints.**

- **No third-party dependency.**  PyYAML is *not* in ``requirements.lock``,
  so importing it would break CI.  The trigger-block parser is imported
  from ``ci_trigger_audit`` rather than reimplemented — one source of
  truth for the YAML subset.
- **Read-only.**  The audit never merges, never pushes, never rewrites a
  workflow.  It reports; a human decides.
- **Degrades honestly.**  When the pull request list cannot be obtained
  (no network, no ``gh``, no token), the script says so and exits
  non-zero rather than reporting a vacuous success.

Usage::

    python3 scripts/pr_coverage_audit.py                 # all open pull requests
    python3 scripts/pr_coverage_audit.py --pr 63          # one pull request
    python3 scripts/pr_coverage_audit.py --json           # machine-readable
    python3 scripts/pr_coverage_audit.py --require-checks  # CI gate mode
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ci_trigger_audit import (  # noqa: E402
    TriggerAudit,
    WorkflowParseError,
    audit_workflow,
)

WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

#: Workflows that are expected to provide pull request verification.
#: ``release.yml`` is deliberately absent: it is a tag-driven publish
#: workflow and was never meant to run on pull requests.
VERIFICATION_WORKFLOWS = ("ci.yml",)


class PrAuditError(RuntimeError):
    """Raised when the pull request state cannot be obtained."""


# ── git / gh access ─────────────────────────────────────────────────────────

def _run(cmd: list[str], cwd: Path | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
        timeout=120,
    )


def gh_available() -> bool:
    """True when the GitHub CLI is installed."""
    return shutil.which("gh") is not None


def list_open_prs(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Return the open pull requests as JSON dicts.

    Raises :class:`PrAuditError` when the list cannot be obtained — the
    caller must not treat an unavailable list as "everything is fine".
    """
    if not gh_available():
        raise PrAuditError("the 'gh' CLI is not installed")
    proc = _run(
        [
            "gh", "pr", "list",
            "--state", "open",
            "--limit", "100",
            "--json",
            "number,title,headRefName,baseRefName,statusCheckRollup,mergeable",
        ],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        raise PrAuditError(
            f"'gh pr list' failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise PrAuditError(f"'gh pr list' returned non-JSON output: {exc}") from exc
    if not isinstance(data, list):
        raise PrAuditError("'gh pr list' did not return a list")
    return data


def get_pr(pr_number: int, repo_root: Path = REPO_ROOT) -> dict[str, Any]:
    """Return a single pull request as a JSON dict."""
    if not gh_available():
        raise PrAuditError("the 'gh' CLI is not installed")
    proc = _run(
        [
            "gh", "pr", "view", str(pr_number),
            "--json",
            "number,title,headRefName,baseRefName,statusCheckRollup,mergeable",
        ],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        raise PrAuditError(
            f"'gh pr view {pr_number}' failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )
    try:
        return json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        raise PrAuditError(f"'gh pr view {pr_number}' returned non-JSON: {exc}") from exc


def read_workflow_at(ref: str, filename: str, repo_root: Path = REPO_ROOT) -> str | None:
    """Return the text of ``filename`` as it exists at ``ref``.

    ``ref`` is usually a pull request's head branch name.  Returns
    ``None`` when the file does not exist at that ref (a branch may simply
    predate the workflow).
    """
    proc = _run(
        ["git", "show", f"{ref}:.github/workflows/{filename}"],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def branch_exists(ref: str, repo_root: Path = REPO_ROOT) -> bool:
    """True when ``ref`` resolves locally (as a branch or a commit)."""
    proc = _run(["git", "rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}"], cwd=repo_root)
    return proc.returncode == 0


# ── Audit model ─────────────────────────────────────────────────────────────

@dataclass
class PrCoverage:
    """The coverage verdict for a single pull request."""

    number: int
    title: str
    head_ref: str
    base_ref: str
    mergeable: str | None = None
    #: The workflow that *would* run, as read from the head branch.
    workflow_name: str | None = None
    #: The pull_request branch filter found on the head branch (None = no filter).
    pull_request_branches: list[str] | None = None
    #: Does the head branch's workflow subscribe to pull_request?
    workflow_subscribes: bool = False
    #: Would the head branch's workflow run for this PR's base branch?
    base_covered: bool = False
    #: How many checks GitHub actually reports for this pull request.
    observed_checks: int = 0
    #: Any reason the verdict could not be established.
    problems: list[str] = field(default_factory=list)

    def __post_init__(self) -> None:
        """Validate the identifying fields at construction time.

        A pull request without a head or base branch cannot be audited at
        all.  Recording that as a *problem* here — rather than only inside
        :func:`audit_pr` — means the invariant holds no matter how the
        object was built, so no caller can accidentally construct a
        "passing" verdict out of an unauditable pull request.
        """
        if not self.head_ref and not any("head branch" in p for p in self.problems):
            self.problems.append("pull request has no head branch")
        if not self.base_ref and not any("base branch" in p for p in self.problems):
            self.problems.append("pull request has no base branch")

    @property
    def is_verified(self) -> bool:
        """True when the pull request is genuinely covered *and* verified.

        Three independent conditions must hold:

        1. the workflow on the head branch subscribes to ``pull_request``;
        2. its filter covers this pull request's base branch;
        3. GitHub actually reports checks for it.

        Condition 3 is what separates *"CI would run"* from *"CI did run"*.
        """
        return (
            self.workflow_subscribes
            and self.base_covered
            and self.observed_checks > 0
            and not self.problems
        )

    @property
    def verdict(self) -> str:
        if self.problems:
            return "unknown"
        if self.is_verified:
            return "verified"
        if not self.workflow_subscribes:
            return "not-subscribed"
        if not self.base_covered:
            return "base-not-covered"
        return "no-checks-reported"

    def to_dict(self) -> dict[str, Any]:
        return {
            "number": self.number,
            "title": self.title,
            "head_ref": self.head_ref,
            "base_ref": self.base_ref,
            "mergeable": self.mergeable,
            "workflow_name": self.workflow_name,
            "pull_request_branches": self.pull_request_branches,
            "workflow_subscribes": self.workflow_subscribes,
            "base_covered": self.base_covered,
            "observed_checks": self.observed_checks,
            "verdict": self.verdict,
            "verified": self.is_verified,
            "problems": list(self.problems),
        }


def _count_checks(status_check_rollup: Any) -> int:
    """Count the check runs GitHub reports for a pull request."""
    if not isinstance(status_check_rollup, list):
        return 0
    return len(status_check_rollup)


def audit_pr(pr: dict[str, Any], repo_root: Path = REPO_ROOT) -> PrCoverage:
    """Audit one pull request's CI coverage.

    The decisive detail: the workflow is read from the pull request's
    **head** branch, because that is what GitHub does when deciding
    whether to start a workflow for the pull request.
    """
    number = int(pr.get("number", 0))
    head = str(pr.get("headRefName") or "")
    base = str(pr.get("baseRefName") or "")

    coverage = PrCoverage(
        number=number,
        title=str(pr.get("title") or ""),
        head_ref=head,
        base_ref=base,
        mergeable=pr.get("mergeable"),
        observed_checks=_count_checks(pr.get("statusCheckRollup")),
    )

    if not head:
        coverage.problems.append("pull request has no head branch")
        return coverage
    if not base:
        coverage.problems.append("pull request has no base branch")
        return coverage

    if not branch_exists(head, repo_root):
        coverage.problems.append(
            f"head branch '{head}' is not available locally; "
            "fetch it before auditing (git fetch origin)"
        )
        return coverage

    for filename in VERIFICATION_WORKFLOWS:
        text = read_workflow_at(head, filename, repo_root)
        if text is None:
            continue

        # Parse the trigger block out of the head-branch copy of the
        # workflow, using the same parser as the file-level audit.
        tmp_name = f".pr-coverage-{number}-{filename}"
        tmp_path = repo_root / tmp_name
        try:
            tmp_path.write_text(text, encoding="utf-8")
            audit = audit_workflow(tmp_path)
        except WorkflowParseError as exc:
            coverage.problems.append(
                f"could not parse '{filename}' on head branch '{head}': {exc}"
            )
            continue
        finally:
            tmp_path.unlink(missing_ok=True)

        coverage.workflow_name = filename
        coverage.pull_request_branches = audit.branches
        coverage.workflow_subscribes = audit.has_pull_request
        coverage.base_covered = audit.covers(base)
        break

    if coverage.workflow_name is None:
        coverage.problems.append(
            "no verification workflow found on the head branch "
            f"({', '.join(VERIFICATION_WORKFLOWS)})"
        )

    return coverage


def audit_prs(
    prs: list[dict[str, Any]],
    repo_root: Path = REPO_ROOT,
) -> list[PrCoverage]:
    return [audit_pr(pr, repo_root) for pr in prs]


def summarize(coverages: list[PrCoverage]) -> dict[str, Any]:
    """Aggregate a list of verdicts into a machine-readable summary."""
    unverified = [c for c in coverages if not c.is_verified]
    return {
        "total": len(coverages),
        "verified": len(coverages) - len(unverified),
        "unverified": len(unverified),
        "unverified_numbers": [c.number for c in unverified],
        "ok": not unverified,
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def _print_report(coverages: list[PrCoverage]) -> None:
    print("🔍 Pull request CI coverage audit")
    print("=" * 68)
    print(
        "GitHub reads workflow definitions from a pull request's HEAD branch,\n"
        "so that is what this audit reads.\n"
    )
    for c in coverages:
        mark = "✅" if c.is_verified else "❌"
        print(f"{mark} PR #{c.number}  {c.title[:52]}")
        print(f"     head → base : {c.head_ref} → {c.base_ref}")
        if c.workflow_name:
            branches = c.pull_request_branches
            shown = "(no filter)" if branches is None else ", ".join(branches)
            print(f"     workflow    : {c.workflow_name}  pull_request filter: {shown}")
            print(f"     base covered: {'yes' if c.base_covered else 'NO'}")
        else:
            print(f"     workflow    : (not found on head branch)")
        print(f"     checks seen : {c.observed_checks}")
        print(f"     verdict     : {c.verdict}")
        for problem in c.problems:
            print(f"     note        : {problem}")
        if c.verdict == "base-not-covered":
            print(
                "     → the workflow on this PR's head branch narrows the\n"
                "       pull_request trigger, so this PR will never get CI.\n"
                "       Fix: merge the trigger fix into this PR's branch, or\n"
                "       retarget this PR at a branch the workflow covers."
            )
        if c.verdict == "no-checks-reported":
            print(
                "     → the workflow would run for this base branch, but GitHub\n"
                "       reports no checks yet (still queued, or the workflow\n"
                "       has not been triggered for this commit)."
            )
        print()

    summary = summarize(coverages)
    print("-" * 68)
    print(
        f"{summary['verified']}/{summary['total']} pull requests are verified by CI."
    )
    if summary["unverified"]:
        print(
            f"❌ {summary['unverified']} pull request(s) are not verified: "
            + ", ".join(f"#{n}" for n in summary["unverified_numbers"])
        )
    else:
        print("✅ Every open pull request is verified by CI.")
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pr", action="append", type=int, default=None,
                        help="audit only this pull request (repeatable)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--require-checks",
        action="store_true",
        help="CI gate mode: fail if any pull request has no checks reported",
    )
    args = parser.parse_args(argv)

    try:
        if args.pr:
            prs = [get_pr(n) for n in args.pr]
        else:
            prs = list_open_prs()
    except PrAuditError as exc:
        print(f"❌ cannot obtain pull request state: {exc}", file=sys.stderr)
        return 2

    if not prs:
        print("No open pull requests to audit.")
        return 0

    coverages = audit_prs(prs)
    summary = summarize(coverages)

    if args.json:
        print(json.dumps({
            "pull_requests": [c.to_dict() for c in coverages],
            "summary": summary,
        }, indent=2))
        return 0 if summary["ok"] else 1

    summary = _print_report(coverages)

    if args.require_checks:
        # Strict mode used by CI: every pull request must have checks.
        missing = [c.number for c in coverages if c.observed_checks == 0]
        if missing:
            print(
                "❌ --require-checks: pull request(s) with no checks reported: "
                + ", ".join(f"#{n}" for n in missing)
            )
            return 1
        print("✅ --require-checks: every pull request has checks reported.")
        return 0

    return 0 if summary["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
