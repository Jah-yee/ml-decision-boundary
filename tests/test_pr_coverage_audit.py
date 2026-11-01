"""Tests for the pull request CI coverage audit (v13 DoD #8).

The invariant under test is the *pull-request-level* version of the one
introduced in v13 DoD #7:

    **Every pull request must actually be verified by CI.**

DoD #7 fixed the trigger block on one branch and added a file-level audit.
That was necessary but not sufficient, because GitHub reads workflow
definitions from a pull request's **head** branch.  A stacked pull request
whose head branch still carries the old, filtered workflow therefore stays
unverified no matter how good the fix is on some other branch.

This repository's PR #63 is the live example: its head branch
(``feat/v13-replay-integrity-guard``) still has ``branches: [master]``
while its base is ``feat/v13-replay-provenance``, so GitHub reports zero
checks for it.

These tests pin:

1. the *verdict logic* — the three independent conditions that make a pull
   request "verified";
2. the *head-branch semantics* — the workflow is read from the head branch,
   not the base branch and not the working tree;
3. the *honest failure mode* — when the pull request list cannot be
   obtained, the audit must not report a vacuous success.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from pr_coverage_audit import (  # noqa: E402
    PrAuditError,
    PrCoverage,
    VERIFICATION_WORKFLOWS,
    audit_pr,
    audit_prs,
    list_open_prs,
    read_workflow_at,
    summarize,
)

CI_WORKFLOW = "ci.yml"

# A workflow whose pull_request trigger is narrowed to master only.
FILTERED_WORKFLOW = """\
name: CI

on:
  push:
    branches: [master, daily/*]
  pull_request:
    branches: [master]

jobs:
  quality-gates:
    runs-on: ubuntu-latest
"""

# A workflow with no pull_request branch filter.
UNFILTERED_WORKFLOW = """\
name: CI

on:
  push:
    branches: [master, daily/*]
  pull_request:

jobs:
  quality-gates:
    runs-on: ubuntu-latest
"""


# ── Helpers ─────────────────────────────────────────────────────────────────

def _pr(
    number: int = 63,
    head: str = "feat/v13-replay-integrity-guard",
    base: str = "feat/v13-replay-provenance",
    checks: int | None = 0,
    title: str = "test pr",
) -> dict:
    rollup = [{"name": f"job-{i}"} for i in range(checks)] if checks is not None else None
    return {
        "number": number,
        "title": title,
        "headRefName": head,
        "baseRefName": base,
        "mergeable": "MERGEABLE",
        "statusCheckRollup": rollup,
    }


# ── Verdict logic ───────────────────────────────────────────────────────────

class TestVerdictLogic:
    """A pull request is verified only when three independent things hold."""

    def test_all_conditions_held_is_verified(self):
        c = PrCoverage(
            number=1,
            title="t",
            head_ref="h",
            base_ref="b",
            workflow_name=CI_WORKFLOW,
            pull_request_branches=None,
            workflow_subscribes=True,
            base_covered=True,
            observed_checks=6,
        )
        assert c.is_verified
        assert c.verdict == "verified"

    def test_no_subscribed_workflow_is_not_verified(self):
        c = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_name=None,
            workflow_subscribes=False,
            base_covered=False,
            observed_checks=0,
        )
        assert not c.is_verified
        assert c.verdict == "not-subscribed"

    def test_base_not_covered_is_not_verified(self):
        c = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_name=CI_WORKFLOW,
            pull_request_branches=["master"],
            workflow_subscribes=True,
            base_covered=False,
            observed_checks=0,
        )
        assert not c.is_verified
        assert c.verdict == "base-not-covered"

    def test_zero_checks_is_not_verified_even_when_base_is_covered(self):
        """The subtle one: the workflow *would* run, but GitHub reports nothing.

        This is the exact state PR #63 was mis-read as "still running".
        """
        c = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_name=CI_WORKFLOW,
            pull_request_branches=None,
            workflow_subscribes=True,
            base_covered=True,
            observed_checks=0,
        )
        assert not c.is_verified
        assert c.verdict == "no-checks-reported"

    def test_any_problem_makes_verdict_unknown(self):
        c = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_subscribes=True,
            base_covered=True,
            observed_checks=6,
            problems=["head branch not fetched"],
        )
        assert not c.is_verified
        assert c.verdict == "unknown"

    def test_verdict_distinguishes_would_run_from_did_run(self):
        """'would run' and 'did run' are different questions."""
        would_run = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_subscribes=True, base_covered=True, observed_checks=0,
        )
        did_run = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_subscribes=True, base_covered=True, observed_checks=6,
        )
        assert would_run.verdict != did_run.verdict
        assert not would_run.is_verified and did_run.is_verified


# ── Head-branch semantics ───────────────────────────────────────────────────

class TestHeadBranchSemantics:
    """The workflow must be read from the pull request's HEAD branch."""

    def test_read_workflow_at_returns_head_content(self, tmp_path):
        """git show <ref>:<path> must return that ref's copy of the file."""
        text = read_workflow_at("origin/master", CI_WORKFLOW, REPO_ROOT)
        assert text is not None
        assert "name: CI" in text

    def test_read_workflow_at_returns_none_for_missing_path(self):
        assert read_workflow_at("origin/master", "no-such-workflow.yml", REPO_ROOT) is None

    def test_audit_reads_head_not_working_tree(self, monkeypatch):
        """The audit must consult the head branch, not the current checkout.

        This is the property that distinguishes DoD #8 from DoD #7: a fix
        that exists only in the working tree (or on some other branch)
        must not make an uncovered pull request look covered.
        """
        calls: list[str] = []

        def fake_read(ref: str, filename: str, repo_root: Path = REPO_ROOT):
            calls.append(ref)
            if ref == "feat/head-with-fix":
                return UNFILTERED_WORKFLOW
            return FILTERED_WORKFLOW

        def fake_exists(ref: str, repo_root: Path = REPO_ROOT) -> bool:
            return True

        monkeypatch.setattr("pr_coverage_audit.read_workflow_at", fake_read)
        monkeypatch.setattr("pr_coverage_audit.branch_exists", fake_exists)

        covered = audit_pr(_pr(head="feat/head-with-fix", base="feat/some-base", checks=6))
        assert covered.base_covered
        assert covered.is_verified

        uncovered = audit_pr(_pr(head="feat/head-without-fix", base="feat/some-base", checks=6))
        assert not uncovered.base_covered
        assert uncovered.verdict == "base-not-covered"
        assert "feat/head-without-fix" in calls


# ── Repository live invariants ──────────────────────────────────────────────

class TestRepositoryInvariants:
    """The live repository must satisfy the invariant right now."""

    def test_every_open_pr_is_covered(self):
        """Every open pull request must be verified by CI.

        This is the invariant DoD #8 exists to protect.  It fails loudly
        whenever a stacked pull request's head branch drifts away from the
        workflow fix.
        """
        try:
            prs = list_open_prs(REPO_ROOT)
        except PrAuditError as exc:
            pytest.skip(f"GitHub state unavailable: {exc}")

        coverages = audit_prs(prs, REPO_ROOT)
        summary = summarize(coverages)
        assert summary["ok"], (
            "pull request(s) "
            + ", ".join(f"#{n}" for n in summary["unverified_numbers"])
            + " are not verified by CI"
        )

    def test_pr_63_is_covered_by_ci(self):
        """The concrete regression: PR #63 accumulated zero checks.

        It is a stacked pull request whose head branch carried the old
        filtered workflow, so CI never started.  Once the trigger fix is
        carried by its head branch, this pull request must be covered.
        """
        try:
            prs = list_open_prs(REPO_ROOT)
        except PrAuditError as exc:
            pytest.skip(f"GitHub state unavailable: {exc}")

        pr63 = [p for p in prs if int(p.get("number", 0)) == 63]
        if not pr63:
            pytest.skip("PR #63 is no longer open")

        coverage = audit_pr(pr63[0], REPO_ROOT)
        assert coverage.workflow_subscribes, (
            "PR #63's head branch must subscribe to the pull_request trigger"
        )
        assert coverage.base_covered, (
            "PR #63's head branch still narrows the pull_request trigger; "
            "it will never receive CI checks"
        )


# ── Honest failure mode ─────────────────────────────────────────────────────

class TestHonestFailureMode:
    """The audit must never report a vacuous success."""

    def test_missing_head_branch_is_a_problem_not_a_pass(self):
        c = PrCoverage(number=1, title="t", head_ref="", base_ref="b")
        assert c.problems

    def test_missing_base_branch_is_a_problem(self):
        c = PrCoverage(number=1, title="t", head_ref="h", base_ref="")
        assert c.problems

    def test_audit_pr_records_problem_when_head_missing(self, monkeypatch):
        monkeypatch.setattr("pr_coverage_audit.branch_exists", lambda *a, **k: False)
        coverage = audit_pr(_pr())
        assert coverage.problems
        assert coverage.verdict == "unknown"
        assert not coverage.is_verified

    def test_summarize_detects_unverified(self):
        good = PrCoverage(
            number=1, title="t", head_ref="h", base_ref="b",
            workflow_subscribes=True, base_covered=True, observed_checks=6,
        )
        bad = PrCoverage(
            number=2, title="t", head_ref="h", base_ref="b",
            workflow_subscribes=True, base_covered=False, observed_checks=0,
        )
        s = summarize([good, bad])
        assert s["total"] == 2
        assert s["verified"] == 1
        assert s["unverified"] == 1
        assert s["unverified_numbers"] == [2]
        assert not s["ok"]


# ── CLI surface ─────────────────────────────────────────────────────────────

class TestCli:
    def test_cli_runs_and_reports(self):
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "pr_coverage_audit.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode in (0, 1), proc.stderr
        payload = json.loads(proc.stdout)
        assert "pull_requests" in payload
        assert "summary" in payload

    def test_verification_workflows_are_non_empty(self):
        assert VERIFICATION_WORKFLOWS
        assert CI_WORKFLOW in VERIFICATION_WORKFLOWS
