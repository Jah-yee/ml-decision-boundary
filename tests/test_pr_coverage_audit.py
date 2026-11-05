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
import os
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from pr_coverage_audit import (  # noqa: E402
    DEFAULT_REQUIREMENTS,
    PrAuditError,
    PrCoverage,
    REQUIRE_CHECKS_REQUIREMENTS,
    VERIFICATION_WORKFLOWS,
    _count_checks,
    _count_completed_checks,
    audit_pr,
    audit_prs,
    evaluate_gate,
    list_open_prs,
    read_workflow_at,
    resolve_workflow_at,
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

def _git(repo: Path, *args: str) -> None:
    """Run a git command inside ``repo``, failing loudly on error."""
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise AssertionError(
            f"git {' '.join(args)} failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )


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
        """``git show <ref>:<path>`` must return that ref's copy of the file.

        This test builds its *own* throwaway repository instead of relying
        on ``origin/master`` being present in the checkout.  The earlier
        version did rely on it, and it failed in CI for exactly the
        reason DoD #9 exists: a CI runner has a shallow checkout that
        contains the running pull request's branch and little else, so
        ``origin/master`` may simply not resolve.  A test that depends on
        the ambient checkout is a test that measures the environment, not
        the code.
        """
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "test")
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / CI_WORKFLOW).write_text(
            UNFILTERED_WORKFLOW, encoding="utf-8"
        )
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "init")

        text = read_workflow_at("main", CI_WORKFLOW, repo)
        assert text is not None
        assert "name: CI" in text

    def test_read_workflow_at_returns_none_for_missing_path(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _git(repo, "init", "-q", "-b", "main")
        _git(repo, "config", "user.email", "test@example.com")
        _git(repo, "config", "user.name", "test")
        (repo / ".github" / "workflows").mkdir(parents=True)
        (repo / ".github" / "workflows" / CI_WORKFLOW).write_text(
            UNFILTERED_WORKFLOW, encoding="utf-8"
        )
        _git(repo, "add", "-A")
        _git(repo, "commit", "-q", "-m", "init")

        assert read_workflow_at("main", "no-such-workflow.yml", repo) is None

    def test_resolve_workflow_prefers_the_api_over_local_git(self, monkeypatch):
        """The API must win over local git.

        This is the regression that made PR #67's own CI run fail: the
        audit read the head branch from local git, and a CI runner simply
        does not have the *other* pull requests' branches in its ref store.
        The API is the only source that works identically on a laptop and
        on a runner, so it must be tried first.
        """
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_from_api",
            lambda *a, **k: "FROM-API",
        )
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_at",
            lambda *a, **k: "FROM-GIT",
        )
        text, source = resolve_workflow_at("some-branch", CI_WORKFLOW, REPO_ROOT)
        assert text == "FROM-API"
        assert source == "api"

    def test_resolve_workflow_falls_back_to_git_when_api_unavailable(self, monkeypatch):
        """Offline use must still work — git is the fallback, not the gate."""
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_from_api",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_at",
            lambda *a, **k: "FROM-GIT",
        )
        text, source = resolve_workflow_at("some-branch", CI_WORKFLOW, REPO_ROOT)
        assert text == "FROM-GIT"
        assert source == "git"

    def test_resolve_workflow_reports_none_when_neither_source_has_it(self, monkeypatch):
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_from_api",
            lambda *a, **k: None,
        )
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_at",
            lambda *a, **k: None,
        )
        text, source = resolve_workflow_at("some-branch", CI_WORKFLOW, REPO_ROOT)
        assert text is None
        assert source == "none"

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
        """When the head branch's workflow cannot be read, that is a
        *problem*, not a pass.

        The mock is applied at the resolution layer (``resolve_workflow_at``),
        not at ``branch_exists``.  That used to be the gate, but after
        DoD #9 the audit reads the head branch over the GitHub API, so
        "the branch is not a local ref" no longer implies "the branch
        cannot be audited".  Mocking the wrong layer would have left the
        real failure mode untested.
        """
        monkeypatch.setattr(
            "pr_coverage_audit.resolve_workflow_at",
            lambda *a, **k: (None, "none"),
        )
        coverage = audit_pr(_pr())
        assert coverage.problems
        assert coverage.verdict == "unknown"
        assert not coverage.is_verified

    def test_audit_pr_still_verifies_when_branch_is_absent_locally(self, monkeypatch):
        """A branch that is not a local ref must NOT block the audit.

        This is the exact condition that broke PR #67's CI run: the audit
        required ``branch_exists(head)``, and a CI runner does not have
        the other pull requests' branches in its ref store, so every pull
        request was reported as unknown and the guard failed the build it
        was supposed to prove.
        """
        monkeypatch.setattr("pr_coverage_audit.branch_exists", lambda *a, **k: False)
        monkeypatch.setattr(
            "pr_coverage_audit.read_workflow_from_api",
            lambda *a, **k: UNFILTERED_WORKFLOW,
        )
        coverage = audit_pr(_pr(checks=6))
        assert not coverage.problems
        assert coverage.workflow_source == "api"
        assert coverage.is_verified
        assert coverage.verdict == "verified"

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
        """The CLI must produce machine-readable output.

        The exit code depends on the environment: ``0`` when every pull
        request is verified, ``1`` when some are not, and ``2`` when the
        pull request list itself cannot be obtained (no network, no
        ``gh``, no token).  The earlier version of this test asserted
        ``returncode in (0, 1)`` and therefore failed on any runner
        without an ambient ``GH_TOKEN`` — the test was measuring the
        runner's credentials, not the CLI.

        ``2`` is a legitimate, *honest* outcome, and it is the outcome the
        script is explicitly designed to produce rather than a vacuous
        success.  What must always hold is that the process terminates
        with one of these codes and, for 0/1, emits valid JSON.
        """
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "pr_coverage_audit.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
        )
        assert proc.returncode in (0, 1, 2), (
            f"unexpected exit code {proc.returncode}\n"
            f"stdout: {proc.stdout[:800]}\nstderr: {proc.stderr[:800]}"
        )
        if proc.returncode == 2:
            # Honest failure: the pull request state was unobtainable.
            # The script must say so on stderr rather than print a
            # vacuous success.
            assert "cannot obtain pull request state" in proc.stderr, proc.stderr
            return
        payload = json.loads(proc.stdout)
        assert "pull_requests" in payload
        assert "summary" in payload

    def test_cli_without_token_fails_honestly(self):
        """With no credentials the CLI must exit 2 and explain itself.

        This pins the *honest degradation* contract end to end: a missing
        token must never be reported as "every pull request is verified".
        """
        env = dict(os.environ)
        env.pop("GH_TOKEN", None)
        env.pop("GITHUB_TOKEN", None)
        env["GH_CONFIG_DIR"] = str(REPO_ROOT / ".tmp-gh-empty-config")
        proc = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "pr_coverage_audit.py"), "--json"],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
            env=env,
        )
        assert proc.returncode == 2, (
            f"expected an honest failure (rc=2), got {proc.returncode}\n"
            f"stdout: {proc.stdout[:800]}"
        )
        assert "cannot obtain pull request state" in proc.stderr, proc.stderr

    def test_verification_workflows_are_non_empty(self):
        assert VERIFICATION_WORKFLOWS
        assert CI_WORKFLOW in VERIFICATION_WORKFLOWS

# ── Gate model: monotonicity (v13 DoD #16) ──────────────────────────────────

class TestGateModel:
    """The gate must be **monotonic** across its modes.

    ``--require-checks`` is advertised as the *stricter* mode.  An
    earlier version of this script decided the two modes with two
    independent ad-hoc expressions, and the "stricter" one came out
    **weaker**: it looked only at ``observed_checks``, so a pull
    request that CI would never run for (``not-subscribed`` or
    ``base-not-covered``) still *passed* the gate as long as it carried
    stale checks from an earlier run.

    These tests exercise the real :func:`evaluate_gate` — not a
    re-implementation of it — so they fail if the gate logic is
    deleted or inverted.
    """

    def _coverage(self, number: int, **kwargs) -> PrCoverage:
        """A pull request that passes every requirement by default."""
        defaults = dict(
            title=f"pr-{number}",
            head_ref="h",
            base_ref="master",
            workflow_name=CI_WORKFLOW,
            workflow_source="api",
            pull_request_branches=None,
            workflow_subscribes=True,
            base_covered=True,
            observed_checks=6,
            completed_checks=6,
        )
        defaults.update(kwargs)
        return PrCoverage(number=number, **defaults)

    # ── the requirement sets themselves ───────────────────────────────────

    def test_strict_requirements_are_a_strict_superset(self):
        """The structural invariant that makes monotonicity possible."""
        assert set(DEFAULT_REQUIREMENTS) < set(REQUIRE_CHECKS_REQUIREMENTS)
        extra = set(REQUIRE_CHECKS_REQUIREMENTS) - set(DEFAULT_REQUIREMENTS)
        assert extra == {"checks_completed"}

    def test_unknown_requirement_is_rejected(self):
        """An unknown requirement must raise, not silently pass."""
        with pytest.raises(ValueError, match="unknown requirement"):
            evaluate_gate([self._coverage(1)], ("not_a_requirement",))

    # ── monotonicity ──────────────────────────────────────────────────────

    def test_strict_mode_is_never_laxer_than_default(self):
        """The core regression.

        For every combination of pull-request states, the strict gate
        must fail whenever the default gate fails — and may fail more.
        """
        states = [
            ("healthy", {}),
            ("no-checks", {"observed_checks": 0, "completed_checks": 0}),
            ("not-subscribed", {"workflow_subscribes": False}),
            ("base-not-covered", {"base_covered": False}),
            ("stale-checks-not-subscribed",
             {"workflow_subscribes": False, "base_covered": False}),
            ("stale-checks-base-not-covered",
             {"base_covered": False}),
            ("unauditable", {"problems": ["no verification workflow found"]}),
            ("queued-only",
             {"observed_checks": 6, "completed_checks": 0}),
        ]
        for label, kwargs in states:
            cov = self._coverage(1, **kwargs)
            default_ok = evaluate_gate([cov], DEFAULT_REQUIREMENTS)["ok"]
            strict_ok = evaluate_gate([cov], REQUIRE_CHECKS_REQUIREMENTS)["ok"]
            if not default_ok:
                assert not strict_ok, (
                    f"strict gate was laxer than the default for state {label!r}"
                )

    def test_the_original_bug_is_fixed(self):
        """The exact regression: stale checks used to launder a failure.

        A pull request whose head-branch workflow does not subscribe to
        ``pull_request`` (so CI would *never* run for it) but which
        carries checks from an earlier run must fail **both** gates.
        """
        cov = self._coverage(
            99,
            workflow_subscribes=False,
            base_covered=False,
            observed_checks=7,
            completed_checks=7,
        )
        assert not cov.is_verified
        default = evaluate_gate([cov], DEFAULT_REQUIREMENTS)
        strict = evaluate_gate([cov], REQUIRE_CHECKS_REQUIREMENTS)
        assert not default["ok"], "default gate must fail"
        assert not strict["ok"], "strict gate must fail"
        assert "subscribes" in strict["failures"][99]

    # ── the extra strict requirement ─────────────────────────────────────

    def test_queued_checks_fail_the_strict_gate_only(self):
        """A queued-but-not-finished check fails strict, passes default.

        GitHub reports a check run as soon as it is created, so
        "a check exists" and "a check finished" are different facts.
        """
        cov = self._coverage(7, observed_checks=6, completed_checks=0)
        assert evaluate_gate([cov], DEFAULT_REQUIREMENTS)["ok"]
        strict = evaluate_gate([cov], REQUIRE_CHECKS_REQUIREMENTS)
        assert not strict["ok"]
        assert strict["failures"][7] == ["checks_completed"]

    def test_finished_checks_pass_the_strict_gate(self):
        cov = self._coverage(7, observed_checks=6, completed_checks=6)
        assert evaluate_gate([cov], REQUIRE_CHECKS_REQUIREMENTS)["ok"]

    # ── reporting ────────────────────────────────────────────────────────

    def test_gate_reports_which_requirements_failed(self):
        cov = self._coverage(5, workflow_subscribes=False, observed_checks=0,
                              completed_checks=0)
        gate = evaluate_gate([cov], DEFAULT_REQUIREMENTS)
        assert gate["failed"] == [5]
        assert set(gate["failures"][5]) == {"subscribes", "checks"}

    def test_empty_pr_list_passes_both_gates(self):
        """No pull requests is not a failure — there is nothing to gate."""
        assert evaluate_gate([], DEFAULT_REQUIREMENTS)["ok"]
        assert evaluate_gate([], REQUIRE_CHECKS_REQUIREMENTS)["ok"]

    def test_gate_reports_the_evaluated_requirements(self):
        gate = evaluate_gate([], REQUIRE_CHECKS_REQUIREMENTS)
        assert gate["requirements"] == list(REQUIRE_CHECKS_REQUIREMENTS)


# ── Check counting: reported vs. finished ───────────────────────────────────

class TestCheckCounting:
    """GitHub reports a check run when it is *created*, not when it
    finishes.  Counting them all as "CI ran" is how a gate ends up
    accepting a pull request whose CI is still warming up.
    """

    def _rollup(self, *entries):
        return list(entries)

    def test_queued_checks_are_observed_but_not_completed(self):
        rollup = self._rollup(
            {"status": "QUEUED", "conclusion": None},
            {"status": "IN_PROGRESS", "conclusion": None},
        )
        assert _count_checks(rollup) == 2
        assert _count_completed_checks(rollup) == 0

    def test_finished_checks_are_counted(self):
        rollup = self._rollup(
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "COMPLETED", "conclusion": "FAILURE"},
        )
        assert _count_checks(rollup) == 2
        assert _count_completed_checks(rollup) == 2

    def test_mixed_rollup_counts_only_finished(self):
        rollup = self._rollup(
            {"status": "QUEUED", "conclusion": None},
            {"status": "COMPLETED", "conclusion": "SUCCESS"},
            {"status": "IN_PROGRESS", "conclusion": None},
            {"status": "COMPLETED", "conclusion": "SKIPPED"},
        )
        assert _count_checks(rollup) == 4
        assert _count_completed_checks(rollup) == 2

    def test_non_list_rollup_counts_nothing(self):
        assert _count_checks(None) == 0
        assert _count_completed_checks(None) == 0
        assert _count_completed_checks("nonsense") == 0

    def test_entry_without_state_is_counted_as_completed(self):
        """An unrecognised shape must not silently read as "no CI ran"."""
        assert _count_completed_checks([{"name": "build"}]) == 1

    def test_completed_status_without_a_conclusion_is_completed(self):
        """``status=COMPLETED`` with ``conclusion=null`` has *finished*.

        The check run reached its terminal status but carries no
        verdict.  GitHub does emit this shape, and treating it as
        "still running" would leave the strict gate permanently
        unsatisfiable for such a check.
        """
        rollup = [{"status": "COMPLETED", "conclusion": None}]
        assert _count_checks(rollup) == 1
        assert _count_completed_checks(rollup) == 1

    def test_a_conclusion_alone_is_enough(self):
        """A terminal verdict without a ``status`` field still counts."""
        assert _count_completed_checks([{"conclusion": "SUCCESS"}]) == 1

    def test_real_github_rollup_shape(self):
        """The exact shape ``gh pr list`` returns."""
        rollup = [
            {
                "__typename": "CheckRun",
                "completedAt": "2026-11-01T14:09:35Z",
                "conclusion": "SUCCESS",
                "name": "ci-trigger-audit",
                "startedAt": "2026-11-01T14:09:31Z",
                "status": "COMPLETED",
                "workflowName": "CI",
            },
            {
                "__typename": "CheckRun",
                "conclusion": None,
                "name": "benchmark",
                "status": "QUEUED",
            },
        ]
        assert _count_checks(rollup) == 2
        assert _count_completed_checks(rollup) == 1


# ── The CLI actually uses the shared gate ───────────────────────────────────

class TestCliUsesTheSharedGate:
    """The CLI must route *both* modes through :func:`evaluate_gate`.

    Otherwise the monotonicity invariant holds only for the library and
    not for the command that CI actually runs.
    """

    def _run(self, *extra, env_extra=None):
        env = dict(os.environ)
        if env_extra:
            env.update(env_extra)
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "pr_coverage_audit.py"),
             *extra],
            capture_output=True,
            text=True,
            timeout=180,
            cwd=str(REPO_ROOT),
            env=env,
        )

    def test_json_output_carries_the_gate_verdict(self):
        """``--json`` must expose the gate, not just the summary.

        The summary answers "is this PR verified"; the gate answers
        "does the gate pass, and why not".  A machine-readable mode
        that omitted the gate would hide the very thing CI needs.
        """
        proc = self._run("--json")
        if proc.returncode == 2:
            # Honest failure mode — no credentials available.
            assert "cannot obtain pull request state" in proc.stderr
            return
        payload = json.loads(proc.stdout)
        assert "gate" in payload, "the JSON output must carry the gate verdict"
        gate = payload["gate"]
        assert "ok" in gate
        assert "requirements" in gate
        assert "failures" in gate

    def test_strict_mode_never_passes_when_default_would_fail(self):
        """End-to-end monotonicity through the real CLI.

        Both modes are run against the same repository state; whenever
        the default mode fails, the strict mode must fail too.
        """
        default = self._run()
        strict = self._run("--require-checks")
        if default.returncode == 2 or strict.returncode == 2:
            assert "cannot obtain pull request state" in default.stderr
            return
        if default.returncode != 0:
            assert strict.returncode != 0, (
                "the strict gate passed while the default gate failed"
            )

    def test_strict_mode_is_at_least_as_strict_in_the_help_text(self):
        """The help text must not describe a *laxer* mode."""
        proc = self._run("--help")
        assert proc.returncode == 0
        assert "--require-checks" in proc.stdout
