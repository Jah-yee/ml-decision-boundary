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

**Head-branch content is fetched over the API, not from local git.**

This is not a preference — it is a correctness requirement, learned the
hard way.  The first version of this script read the head branch with
``git show <branch>:.github/workflows/ci.yml`` and required the branch
to exist as a local ref.  On a developer machine that holds, because
every branch has been fetched.  **In CI it does not hold at all**: the
``pull_request`` event checks out a detached merge commit, so no other
pull request's head branch is materialised locally.  The audit therefore
reported ``(not found on head branch)`` for *every* pull request, judged
all of them unverified, and turned the very CI run that was supposed to
*prove* coverage into the thing that *failed* the build (PR #67, run
41265562901: ``pr-coverage-audit`` FAILED, 0/6 verified).

The fix is to stop depending on the local ref at all: the head branch's
workflow is fetched from the GitHub Contents API, which needs only a
token and works identically on a laptop and on a runner.  Local git is
kept only as a *fallback* for offline use.

Usage::

    python3 scripts/pr_coverage_audit.py                 # all open pull requests
    python3 scripts/pr_coverage_audit.py --pr 63          # one pull request
    python3 scripts/pr_coverage_audit.py --json           # machine-readable
    python3 scripts/pr_coverage_audit.py --require-checks  # stricter gate mode

**The gate is monotonic.**

Both modes are decided by one function, :func:`evaluate_gate`, over a
requirement set.  ``--require-checks`` uses a *strict superset* of the
default requirements, so it can only ever turn a pass into a failure,
never the other way round.

This is not a stylistic preference.  An earlier version decided the two
modes with two independent ad-hoc expressions, and the "stricter" mode
came out **weaker**: it looked only at ``observed_checks``, so a pull
request that CI would never run for (``not-subscribed`` or
``base-not-covered``) still passed the gate as long as it carried stale
checks from an earlier run.  A gate mode that is laxer than the default
is a trap: it looks like a safety net and behaves like a sieve.
"""
from __future__ import annotations

import argparse
import base64
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

    This is the **local git** reader.  It is only correct when ``ref``
    happens to be materialised locally — which is true on a developer
    machine and *false* in CI.  See :func:`read_workflow_from_api` and
    :func:`resolve_workflow_at` for the reader that is correct in both.
    """
    proc = _run(
        ["git", "show", f"{ref}:.github/workflows/{filename}"],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def read_workflow_from_api(
    ref: str,
    filename: str,
    repo_root: Path = REPO_ROOT,
    repo_slug: str | None = None,
) -> str | None:
    """Fetch ``filename`` at ``ref`` from the GitHub Contents API.

    Returns the decoded file text, or ``None`` when the file does not
    exist at that ref.

    Why the API rather than local git: see the module docstring.  In CI
    the pull request's *own* head branch is the only thing checked out,
    so every *other* open pull request's head branch is absent locally —
    reading them from git therefore reports "not found" for all of them.

    The API path needs a token.  ``gh`` is used as the transport because
    it already knows how to authenticate (it reads ``GH_TOKEN`` /
    ``GITHUB_TOKEN`` from the environment itself) and how to talk to
    GitHub Enterprise hosts, and it is present on every GitHub Actions
    runner.
    """
    if not gh_available():
        return None

    slug = repo_slug or _detect_repo_slug(repo_root)
    if not slug:
        return None

    path = f".github/workflows/{filename}"
    proc = _run(
        [
            "gh", "api",
            "--method", "GET",
            f"repos/{slug}/contents/{path}",
            "-f", f"ref={ref}",
            "--jq", ".content",
        ],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        return None
    raw = proc.stdout.strip()
    if not raw:
        return None
    try:
        return base64.b64decode(raw).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None


def _detect_repo_slug(repo_root: Path = REPO_ROOT) -> str | None:
    """Return ``owner/repo`` for the checkout, or ``None`` if unknown."""
    proc = _run(["git", "remote", "get-url", "origin"], cwd=repo_root)
    if proc.returncode != 0:
        return None
    url = proc.stdout.strip()
    if not url:
        return None
    # Handle both https://github.com/owner/repo.git and
    # git@github.com:owner/repo.git forms.
    tail = url.rstrip("/")
    if tail.endswith(".git"):
        tail = tail[: -len(".git")]
    if ":" in tail and "/" not in tail.split(":")[-1]:
        tail = tail.split(":")[-1]
    parts = [p for p in tail.replace(":", "/").split("/") if p]
    if len(parts) < 2:
        return None
    return "/".join(parts[-2:])


def resolve_workflow_at(
    ref: str,
    filename: str,
    repo_root: Path = REPO_ROOT,
    repo_slug: str | None = None,
) -> tuple[str | None, str]:
    """Return ``(workflow_text, source)`` for ``filename`` at ``ref``.

    ``source`` is one of:

    - ``"api"``   — fetched from the GitHub Contents API (authoritative;
      works in CI where local refs are absent);
    - ``"git"``   — read from a local git ref (offline fallback);
    - ``"none"``  — the file could not be found at ``ref``.

    The API is tried first *on purpose*.  Local git is only a fallback
    for offline use; using it first would make the audit's result depend
    on which branches happen to be checked out, which is exactly the bug
    this reader was written to fix.
    """
    text = read_workflow_from_api(ref, filename, repo_root, repo_slug=repo_slug)
    if text is not None:
        return text, "api"

    text = read_workflow_at(ref, filename, repo_root)
    if text is not None:
        return text, "git"

    return None, "none"


def branch_exists(ref: str, repo_root: Path = REPO_ROOT) -> bool:
    """True when ``ref`` resolves locally (as a branch or a commit).

    This is **not** a reliable indicator of "can this branch be audited".
    A branch can be perfectly real and still absent from a CI runner's
    ref store.  It is kept only as a cheap pre-check for the local-git
    fallback path.
    """
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
    #: Where the head-branch workflow text came from ("api" / "git" / "none").
    workflow_source: str | None = None
    #: The pull_request branch filter found on the head branch (None = no filter).
    pull_request_branches: list[str] | None = None
    #: Does the head branch's workflow subscribe to pull_request?
    workflow_subscribes: bool = False
    #: Would the head branch's workflow run for this PR's base branch?
    base_covered: bool = False
    #: How many checks GitHub actually reports for this pull request.
    observed_checks: int = 0
    #: How many of those checks have actually *finished* (as opposed to
    #: still being queued or in progress).  GitHub reports a check run
    #: for a pull request as soon as it is *created*, so
    #: :attr:`observed_checks` counts runs that have not produced a
    #: verdict yet.  A gate that only looks at ``observed_checks`` would
    #: accept a pull request whose CI is still warming up.
    completed_checks: int = 0
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
    def has_completed_checks(self) -> bool:
        """True when at least one reported check has actually finished."""
        return self.completed_checks > 0

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
            "workflow_source": self.workflow_source,
            "pull_request_branches": self.pull_request_branches,
            "workflow_subscribes": self.workflow_subscribes,
            "base_covered": self.base_covered,
            "observed_checks": self.observed_checks,
            "completed_checks": self.completed_checks,
            "verdict": self.verdict,
            "verified": self.is_verified,
            "problems": list(self.problems),
        }


def _count_checks(status_check_rollup: Any) -> int:
    """Count the check runs GitHub reports for a pull request."""
    if not isinstance(status_check_rollup, list):
        return 0
    return len(status_check_rollup)


#: Check *conclusions* that mean "this check has produced a verdict".
#: Everything else (``QUEUED``, ``PENDING``, ``IN_PROGRESS``,
#: ``WAITING``, ``REQUESTED``) means the check has not finished yet.
COMPLETED_CHECK_STATUSES: frozenset[str] = frozenset({
    "SUCCESS",
    "FAILURE",
    "ERROR",
    "CANCELLED",
    "TIMED_OUT",
    "ACTION_REQUIRED",
    "NEUTRAL",
    "SKIPPED",
    "STALE",
})

#: Check *statuses* that mean "this check has finished running".
#: ``COMPLETED`` is the terminal status of a check run; the verdict
#: itself lives in ``conclusion`` and may legitimately be ``None``.
COMPLETED_CHECK_RUN_STATUSES: frozenset[str] = frozenset({
    "COMPLETED",
})


def _count_completed_checks(status_check_rollup: Any) -> int:
    """Count the reported check runs that have actually *finished*.

    GitHub creates a check run as soon as a workflow starts, so the
    raw rollup length counts runs that are still queued or in
    progress.  A check that has not finished has not produced a
    verdict yet, and treating "queued" as "passed" is exactly the
    kind of silent hole a gate must not have.

    A check counts as finished when **either** its ``conclusion`` names
    a terminal verdict **or** its ``status`` is ``COMPLETED``.  The
    two are independent: a check run with ``status=COMPLETED`` and
    ``conclusion=null`` has finished running but carries no verdict
    (this shape does occur), and a check with only a ``conclusion`` and
    no ``status`` is already terminal.

    An entry with neither field is counted as completed, so that a
    rollup in an unfamiliar shape cannot silently read as "no CI ran".
    """
    if not isinstance(status_check_rollup, list):
        return 0
    completed = 0
    for entry in status_check_rollup:
        if not isinstance(entry, dict):
            continue
        conclusion = entry.get("conclusion")
        status = entry.get("status")
        if isinstance(conclusion, str) and conclusion.upper() in COMPLETED_CHECK_STATUSES:
            completed += 1
            continue
        if isinstance(status, str) and status.upper() in COMPLETED_CHECK_RUN_STATUSES:
            completed += 1
            continue
        if conclusion is None and status is None:
            # No state information at all — count it, so that a rollup
            # in an unfamiliar shape cannot silently read as "no CI ran".
            completed += 1
    return completed


def audit_pr(
    pr: dict[str, Any],
    repo_root: Path = REPO_ROOT,
    repo_slug: str | None = None,
) -> PrCoverage:
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
        completed_checks=_count_completed_checks(pr.get("statusCheckRollup")),
    )

    if not head:
        coverage.problems.append("pull request has no head branch")
        return coverage
    if not base:
        coverage.problems.append("pull request has no base branch")
        return coverage

    for filename in VERIFICATION_WORKFLOWS:
        text, source = resolve_workflow_at(
            head, filename, repo_root, repo_slug=repo_slug
        )
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
        coverage.workflow_source = source
        coverage.pull_request_branches = audit.branches
        coverage.workflow_subscribes = audit.has_pull_request
        coverage.base_covered = audit.covers(base)
        break

    if coverage.workflow_name is None:
        # The head branch's workflow could not be read at all.  Report it
        # honestly as an unknown verdict — never as "not covered" (which
        # would be a guess) and never as a pass.
        detail = ""
        if not branch_exists(head, repo_root):
            detail = (
                " (the branch is also not available locally, and the "
                "GitHub API could not be reached — a token may be missing)"
            )
        coverage.problems.append(
            "no verification workflow found on the head branch "
            f"({', '.join(VERIFICATION_WORKFLOWS)}){detail}"
        )

    return coverage


def audit_prs(
    prs: list[dict[str, Any]],
    repo_root: Path = REPO_ROOT,
    repo_slug: str | None = None,
) -> list[PrCoverage]:
    return [audit_pr(pr, repo_root, repo_slug=repo_slug) for pr in prs]


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


# ── Gate model ──────────────────────────────────────────────────────────────

#: The requirement set evaluated by the *default* gate.
#:
#: A pull request satisfies the default gate when all of these hold:
#:
#: ``subscribes``
#:     the workflow on the pull request's head branch listens to
#:     ``pull_request`` at all;
#: ``base_covered``
#:     that workflow's ``pull_request`` filter covers this pull
#:     request's own base branch;
#: ``checks``
#:     GitHub actually reports at least one check for it;
#: ``auditable``
#:     no problem prevented the audit from reaching a verdict.
DEFAULT_REQUIREMENTS: tuple[str, ...] = (
    "subscribes",
    "base_covered",
    "checks",
    "auditable",
)

#: The requirement set evaluated by the ``--require-checks`` gate.
#:
#: **This set is a strict superset of :data:`DEFAULT_REQUIREMENTS`.**
#: That is the whole point: a stricter *mode* of the same gate must never
#: be laxer than the default.  The extra requirement is that the
#: observed checks must actually have *run* — a check that is merely
#: *queued* has been reported by GitHub but has not produced a verdict
#: yet, so "CI has started" is not the same as "CI has finished".
REQUIRE_CHECKS_REQUIREMENTS: tuple[str, ...] = DEFAULT_REQUIREMENTS + (
    "checks_completed",
)


def _requirement_failed(c: PrCoverage, requirement: str) -> bool:
    """True when ``c`` fails a single requirement.

    Each requirement is checked independently so that the gate can
    report *why* a pull request failed rather than just *that* it did.
    """
    if requirement == "subscribes":
        return not c.workflow_subscribes
    if requirement == "base_covered":
        return not c.base_covered
    if requirement == "checks":
        return c.observed_checks <= 0
    if requirement == "auditable":
        return bool(c.problems)
    if requirement == "checks_completed":
        return c.completed_checks <= 0
    raise ValueError(f"unknown requirement: {requirement!r}")


def evaluate_gate(
    coverages: list[PrCoverage],
    requirements: tuple[str, ...] = DEFAULT_REQUIREMENTS,
) -> dict[str, Any]:
    """Evaluate the gate against ``coverages``.

    This is the **single** place where "does this gate pass?" is
    decided.  Every mode of the CLI — default and ``--require-checks`` —
    goes through it, which is what makes the modes *monotonic*: adding
    a requirement can only ever turn a pass into a failure, never the
    other way round.

    Returns a dict with:

    ``ok``
        whether the gate passes;
    ``failed``
        the pull request numbers that failed the gate;
    ``failures``
        a mapping of pull request number to the requirements it failed;
    ``requirements``
        the requirement set that was evaluated.
    """
    failures: dict[int, list[str]] = {}
    for c in coverages:
        failed = [r for r in requirements if _requirement_failed(c, r)]
        if failed:
            failures[c.number] = failed
    return {
        "ok": not failures,
        "failed": sorted(failures),
        "failures": {n: failures[n] for n in sorted(failures)},
        "requirements": list(requirements),
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
            print(f"     read from   : {c.workflow_source}")
            print(f"     base covered: {'yes' if c.base_covered else 'NO'}")
        else:
            print(f"     workflow    : (not found on head branch)")
        print(f"     checks seen : {c.observed_checks} ({c.completed_checks} finished)")
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
        help=(
            "stricter CI gate mode: additionally require that the reported "
            "checks have actually finished (not merely been queued)"
        ),
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

    # The gate requirements are chosen here, and the *same* evaluator
    # decides pass/fail for every mode.  Because
    # REQUIRE_CHECKS_REQUIREMENTS is a strict superset of
    # DEFAULT_REQUIREMENTS, the stricter mode can only ever be
    # *at least as strict* as the default one.  An earlier version of
    # this script decided the two modes with two independent ad-hoc
    # expressions, which made --require-checks strictly *weaker* than
    # the default: a pull request that CI would never run for (not
    # subscribed / base not covered) still passed the gate as long as
    # it carried stale checks from an earlier run.
    requirements = (
        REQUIRE_CHECKS_REQUIREMENTS if args.require_checks else DEFAULT_REQUIREMENTS
    )
    gate = evaluate_gate(coverages, requirements)

    if args.json:
        print(json.dumps({
            "pull_requests": [c.to_dict() for c in coverages],
            "summary": summary,
            "gate": gate,
        }, indent=2))
        return 0 if gate["ok"] else 1

    summary = _print_report(coverages)

    if not gate["ok"]:
        for number, failed in gate["failures"].items():
            print(f"❌ gate: PR #{number} failed requirement(s): {', '.join(failed)}")
        return 1

    if args.require_checks:
        print(
            "✅ --require-checks: every pull request has finished checks."
        )
        return 0

    return 0


if __name__ == "__main__":
    sys.exit(main())
