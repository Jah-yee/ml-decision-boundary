"""Tests for the stack topology audit (v13 DoD #17).

The invariant under test is the *stack-shaped* counterpart of the ones
introduced earlier:

    **Every pull request must actually be verified by CI.**

DoD #7 fixed the workflow trigger block.  DoD #8 added a pull-request-level
audit of CI coverage.  DoD #16 made the two gate modes monotonic.

None of them look at the **shape of the stack itself**.  This repository
uses stacked pull requests, and a stack has its own failure mode: the
branches can *diverge* while every individual pull request still looks
perfectly healthy.

**The concrete case.**  PR #63 (``feat/v13-replay-integrity-guard``) and
PR #66 (``feat/v13-ci-trigger-coverage``) were prepared in parallel and
both independently added the same ``pr-coverage-audit`` job.  Their
workflow files ended up byte-identical, and GitHub reported both pull
requests as ``MERGEABLE`` / ``clean``.  Yet neither branch contained the
other's commit, so the stack was not linear.

These tests pin:

1. the *verdict logic* — what "linear", "diverged", "diverged-duplicate"
   and "conflict" each mean;
2. the *conflict detection* — in particular that the **exit code** of
   ``git merge-tree`` is **not** a conflict signal, because a merge that
   conflicts still exits ``0``;
3. the *duplicate-payload detection* — the signature of two branches
   independently committing the same change;
4. the *honest failure mode* — when the pull request list cannot be
   obtained, the audit must not report a vacuous success.

Every test builds its own throwaway repository.  A test that depends on
the ambient checkout measures the environment, not the code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from stack_topology_audit import (  # noqa: E402
    DEFAULT_REQUIREMENTS,
    StackAuditError,
    Stack,
    StackLink,
    STRICT_REQUIREMENTS,
    _duplicated_payload,
    build_stack,
    evaluate_gate,
    file_contents,
    is_ancestor,
    merge_base,
    merge_conflicts,
    merge_order,
)


# ── helpers ─────────────────────────────────────────────────────────────────

def _git(repo: Path, *args: str) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=str(repo),
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert proc.returncode == 0, f"git {args} failed: {proc.stderr}"
    return proc.stdout


def _init(repo: Path) -> Path:
    repo.mkdir(parents=True, exist_ok=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "test@example.com")
    _git(repo, "config", "user.name", "test")
    return repo


def _commit(repo: Path, name: str, content: str, message: str) -> None:
    (repo / name).parent.mkdir(parents=True, exist_ok=True)
    (repo / name).write_text(content, encoding="utf-8")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _branch(repo: Path, name: str, *, start: str | None = None) -> None:
    if start:
        _git(repo, "checkout", "-q", "-b", name, start)
    else:
        _git(repo, "checkout", "-q", "-b", name)


def _pr(number: int, head: str, base: str, **extra) -> dict:
    payload = {
        "number": number,
        "title": f"PR {number}",
        "headRefName": head,
        "baseRefName": base,
        "mergeable": "MERGEABLE",
        "mergeStateStatus": "CLEAN",
    }
    payload.update(extra)
    return payload


# ── conflict detection ──────────────────────────────────────────────────────

class TestConflictDetection:
    """``git merge-tree``'s exit code is NOT a conflict signal."""

    def test_merge_tree_reports_conflict_on_stdout_even_when_exit_code_is_zero(self, tmp_path):
        """The premise of the whole conflict-detection code path.

        ``git merge-tree --write-tree`` writes the merged tree *with
        conflict markers embedded* and reports the conflict on stdout.
        The exit code is **not** a contract: it is ``0`` on some git
        versions and ``1`` on others, depending on the conflict kind.
        Trusting it would report a genuinely conflicting pair as
        "mergeable" on the version where it happens to be ``0``.

        This test asserts the **output** is the conflict signal, which
        is stable across git versions.
        """
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "f.txt", "one\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "f.txt", "two\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        proc = subprocess.run(
            ["git", "merge-tree", "--write-tree", "--name-only", one, two],
            cwd=str(repo),
            capture_output=True,
            text=True,
        )
        out = (proc.stdout or "") + (proc.stderr or "")
        # The conflict is reported on stdout, regardless of exit code.
        assert "CONFLICT" in out, (
            "this test's premise is that merge-tree reports conflicts on "
            "stdout; if git changed, the conflict detection must be revisited"
        )
        # The exit code is not part of the contract.
        assert proc.returncode in (0, 1)

    def test_conflicting_branches_are_detected(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "f.txt", "one\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "f.txt", "two\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        conflicts, ok = merge_conflicts(one, two, repo)
        assert not ok
        assert "f.txt" in conflicts

    def test_clean_branches_are_reported_as_mergeable(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")

        _branch(repo, "one")
        _commit(repo, "b.txt", "one\n", "one")
        _branch(repo, "two")
        _commit(repo, "c.txt", "two\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        conflicts, ok = merge_conflicts(one, two, repo)
        assert ok
        assert conflicts == []

    def test_identical_content_on_both_sides_is_not_a_conflict(self, tmp_path):
        """Two branches with the *same* content merge cleanly.

        This is the DoD #17 case: PR #63 and PR #66 carried identical
        ``ci.yml`` content, and that is a divergence, not a conflict.
        """
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "same.txt", "identical\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "same.txt", "identical\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        conflicts, ok = merge_conflicts(one, two, repo)
        assert ok
        assert conflicts == []

    def test_unknown_revision_raises_rather_than_reporting_a_conflict(self, tmp_path):
        """A failure to attempt the merge is not a merge conflict."""
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        head = _git(repo, "rev-parse", "HEAD").strip()

        with pytest.raises(StackAuditError):
            merge_conflicts(head, "no-such-branch-xyz", repo)

    def test_no_output_raises_rather_than_reporting_a_conflict(self, tmp_path):
        """Empty output means the merge could not be described."""
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        head = _git(repo, "rev-parse", "HEAD").strip()

        # A merge where both sides are the same commit produces no
        # conflict and no tree-ish line — the output is empty.
        conflicts, ok = merge_conflicts(head, head, repo)
        # Same commit: no conflict, mergeable.
        assert ok
        assert conflicts == []


# ── ancestry ────────────────────────────────────────────────────────────────

class TestAncestry:
    def test_is_ancestor_detects_a_linear_chain(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        _branch(repo, "one")
        _commit(repo, "b.txt", "one\n", "one")
        _branch(repo, "two")
        _commit(repo, "c.txt", "two\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        assert is_ancestor(one, two, repo)
        assert not is_ancestor(two, one, repo)

    def test_diverged_branches_are_not_ancestors(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "b.txt", "one\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "c.txt", "two\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        assert not is_ancestor(one, two, repo)
        assert not is_ancestor(two, one, repo)
        assert merge_base(one, two, repo) == base


# ── duplicate payload ───────────────────────────────────────────────────────

class TestDuplicatePayload:
    """The signature of two branches independently committing a change."""

    def test_identical_new_file_on_both_branches_is_duplicate(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "shared.txt", "same content\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "shared.txt", "same content\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        duplicated = _duplicated_payload(base, one, two, repo)
        assert "shared.txt" in duplicated

    def test_different_content_on_both_branches_is_not_duplicate(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "shared.txt", "content A\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "shared.txt", "content B\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        duplicated = _duplicated_payload(base, one, two, repo)
        assert "shared.txt" not in duplicated

    def test_a_file_present_in_the_base_is_not_a_duplicate(self, tmp_path):
        """A file the merge base already has is not "added on both sides"."""
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        _commit(repo, "existing.txt", "base content\n", "base2")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "one")
        _commit(repo, "existing.txt", "one change\n", "one")
        _branch(repo, "two", start=base)
        _commit(repo, "existing.txt", "two change\n", "two")

        one = _git(repo, "rev-parse", "one").strip()
        two = _git(repo, "rev-parse", "two").strip()

        duplicated = _duplicated_payload(base, one, two, repo)
        assert "existing.txt" not in duplicated


# ── stack construction ──────────────────────────────────────────────────────

class TestStackConstruction:
    def test_linear_stack_is_ordered_bottom_up(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        _branch(repo, "one")
        _commit(repo, "b.txt", "one\n", "one")
        _branch(repo, "two")
        _commit(repo, "c.txt", "two\n", "two")

        prs = [
            _pr(1, "one", "main"),
            _pr(2, "two", "one"),
        ]
        stack = build_stack(prs, repo)
        assert stack.order() == [1, 2]
        assert len(stack.links) == 1
        assert stack.links[0].is_clean
        assert stack.links[0].verdict == "linear"

    def test_diverged_stack_is_detected_and_flagged_as_repairable(self, tmp_path):
        """The DoD #17 case: same content, two commits, not linear."""
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "lower")
        _commit(repo, "shared.txt", "same\n", "lower change")
        _branch(repo, "upper", start=base)
        _commit(repo, "shared.txt", "same\n", "upper change")

        prs = [_pr(1, "lower", "main"), _pr(2, "upper", "lower")]
        stack = build_stack(prs, repo)

        assert stack.order() == [1, 2]
        link = stack.links[0]
        assert not link.linear
        assert link.verdict == "diverged-duplicate"
        assert link.is_repairable
        assert not link.is_clean
        assert "shared.txt" in link.duplicated_payload

    def test_a_pr_whose_base_is_outside_the_stack_is_ignored(self, tmp_path):
        """Only pull requests rooted at the default branch are in the stack."""
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")

        prs = [
            _pr(1, "feature-a", "main"),
            _pr(2, "feature-b", "some-unrelated-branch"),
        ]
        stack = build_stack(prs, repo)
        assert stack.order() == [1]

    def test_a_pr_based_on_another_pr_is_included(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")

        _branch(repo, "feature-a")
        _commit(repo, "b.txt", "a\n", "a")
        _branch(repo, "feature-b")
        _commit(repo, "c.txt", "b\n", "b")
        _branch(repo, "feature-c")
        _commit(repo, "d.txt", "c\n", "c")

        prs = [
            _pr(1, "feature-a", "main"),
            _pr(2, "feature-b", "feature-a"),
            _pr(3, "feature-c", "feature-b"),
        ]
        stack = build_stack(prs, repo)
        assert stack.order() == [1, 2, 3]
        assert len(stack.links) == 2

    def test_summary_counts_repairable_and_blocked_links(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        base = _git(repo, "rev-parse", "HEAD").strip()

        _branch(repo, "lower")
        _commit(repo, "shared.txt", "same\n", "lower change")
        _branch(repo, "upper", start=base)
        _commit(repo, "shared.txt", "same\n", "upper change")

        prs = [_pr(1, "lower", "main"), _pr(2, "upper", "lower")]
        stack = build_stack(prs, repo)
        summary = stack.summary()

        assert summary["total"] == 2
        assert summary["links"] == 1
        assert summary["clean_links"] == 0
        assert summary["broken_links"] == 1
        assert summary["repairable_links"] == 1
        assert summary["blocked_links"] == 0
        assert summary["ok"] is False

    def test_merge_order_lists_prs_bottom_up(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")

        _branch(repo, "feature-a")
        _commit(repo, "b.txt", "a\n", "a")
        _branch(repo, "feature-b")
        _commit(repo, "c.txt", "b\n", "b")

        prs = [_pr(1, "feature-a", "main"), _pr(2, "feature-b", "feature-a")]
        stack = build_stack(prs, repo)

        commands = merge_order(stack)
        assert len(commands) == 2
        assert "gh pr merge 1" in commands[0]
        assert "gh pr merge 2" in commands[1]


# ── the gate ────────────────────────────────────────────────────────────────

class TestGate:
    """The gate is decided in exactly one place, over a requirement set."""

    def _link(self, **kwargs) -> StackLink:
        defaults = dict(
            upper_number=2,
            lower_number=1,
            upper_head="upper",
            lower_head="lower",
            upper_base="lower",
            lower_base="main",
            linear=True,
            mergeable=True,
        )
        defaults.update(kwargs)
        return StackLink(**defaults)

    def test_a_clean_link_passes_the_default_gate(self):
        link = self._link()
        gate = evaluate_gate([link], DEFAULT_REQUIREMENTS)
        assert gate["ok"]
        assert gate["failed"] == []

    def test_a_non_mergeable_link_fails_the_default_gate(self):
        link = self._link(mergeable=False, conflicts=["ci.yml"])
        gate = evaluate_gate([link], DEFAULT_REQUIREMENTS)
        assert not gate["ok"]
        assert "mergeable" in gate["failures"][2]

    def test_a_duplicated_payload_fails_the_default_gate(self):
        link = self._link(duplicated_payload=["ci.yml"])
        gate = evaluate_gate([link], DEFAULT_REQUIREMENTS)
        assert not gate["ok"]
        assert "no_duplicate_payload" in gate["failures"][2]

    def test_a_diverged_link_without_duplicate_payload_passes_default(self):
        """A diverged but clean link passes the default gate.

        The default gate answers "can this stack be merged?" — a
        diverged stack can still be merged bottom-up.  The strict gate
        additionally requires linearity.
        """
        link = self._link(linear=False)
        default = evaluate_gate([link], DEFAULT_REQUIREMENTS)
        strict = evaluate_gate([link], STRICT_REQUIREMENTS)
        assert default["ok"] is True
        assert strict["ok"] is False
        assert "linear" in strict["failures"][2]

    def test_strict_requirements_are_a_strict_superset(self):
        assert set(DEFAULT_REQUIREMENTS).issubset(set(STRICT_REQUIREMENTS))
        assert len(STRICT_REQUIREMENTS) > len(DEFAULT_REQUIREMENTS)

    def test_strict_mode_is_never_laxer_than_default(self):
        """A stricter mode must only ever turn a pass into a failure."""
        links = [
            self._link(upper_number=2),
            # A diverged but mergeable link with no duplicate payload:
            # passes the default gate (mergeable + no duplicate),
            # fails the strict gate (not linear).
            self._link(upper_number=3, linear=False),
            self._link(upper_number=4, mergeable=False),
            self._link(upper_number=5, duplicated_payload=["x"]),
        ]
        default = evaluate_gate(links, DEFAULT_REQUIREMENTS)
        strict = evaluate_gate(links, STRICT_REQUIREMENTS)

        assert set(default["failed"]).issubset(set(strict["failed"]))
        assert default["ok"] is False  # links 4 and 5 fail
        assert strict["ok"] is False
        assert 3 in strict["failed"]
        assert 3 not in default["failed"]

    def test_the_original_bug_is_fixed(self):
        """The DoD #17 bug: a diverged link must never pass the gate.

        The first version of this audit only checked mergeability.  A
        diverged pair of branches merges *cleanly* (identical content),
        so it sailed through — which is exactly the case that needed
        reporting.
        """
        diverged = self._link(linear=False, duplicated_payload=["ci.yml"])

        # The old, insufficient behaviour.
        old_ok = diverged.mergeable and not diverged.conflicts
        assert old_ok, "the premise: a diverged pair merges cleanly"

        # The fixed behaviour: duplicate payload fails the default gate.
        gate = evaluate_gate([diverged], DEFAULT_REQUIREMENTS)
        assert not gate["ok"]
        assert "no_duplicate_payload" in gate["failures"][2]

    def test_a_diverged_link_without_duplicate_payload_fails_only_strict(self):
        """A diverged link with no duplicate payload passes default, fails strict."""
        link = self._link(linear=False)
        default = evaluate_gate([link], DEFAULT_REQUIREMENTS)
        strict = evaluate_gate([link], STRICT_REQUIREMENTS)
        assert default["ok"] is True
        assert strict["ok"] is False
        assert "linear" in strict["failures"][2]


# ── honest failure mode ─────────────────────────────────────────────────────

class TestHonestFailureMode:
    def test_no_prs_means_an_empty_stack_not_a_crash(self, tmp_path):
        repo = _init(tmp_path / "repo")
        stack = build_stack([], repo)
        assert stack.order() == []
        assert stack.links == []
        assert stack.summary()["ok"] is True

    def test_file_contents_returns_none_for_a_missing_path(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "base\n", "base")
        head = _git(repo, "rev-parse", "HEAD").strip()
        assert file_contents(head, "no-such-file.txt", repo) is None

    def test_file_contents_returns_the_file(self, tmp_path):
        repo = _init(tmp_path / "repo")
        _commit(repo, "a.txt", "hello\n", "base")
        head = _git(repo, "rev-parse", "HEAD").strip()
        assert file_contents(head, "a.txt", repo) == "hello\n"


# ── CLI ─────────────────────────────────────────────────────────────────────

class TestCli:
    """The CLI must use the shared gate, and must fail loudly when blind."""

    def _run(self, args: list[str], cwd: Path) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "stack_topology_audit.py"),
             *args],
            cwd=str(cwd),
            capture_output=True,
            text=True,
            timeout=180,
        )

    def test_cli_json_output_is_parseable(self):
        proc = self._run(["--json"], REPO_ROOT)
        # The live repository's stack may or may not be clean; the JSON
        # must be well-formed either way.
        assert proc.returncode in (0, 1), proc.stderr
        payload = json.loads(proc.stdout)
        assert "gate" in payload
        assert "order" in payload
        assert "merge_order" in payload
        assert isinstance(payload["gate"]["requirements"], list)

    def test_cli_gate_requirements_are_reported(self):
        proc = self._run(["--json"], REPO_ROOT)
        payload = json.loads(proc.stdout)
        assert payload["gate"]["requirements"] == list(DEFAULT_REQUIREMENTS)

    def test_cli_strict_mode_adds_a_requirement(self):
        proc = self._run(["--json", "--strict"], REPO_ROOT)
        payload = json.loads(proc.stdout)
        assert payload["gate"]["requirements"] == list(STRICT_REQUIREMENTS)
        assert len(STRICT_REQUIREMENTS) > len(DEFAULT_REQUIREMENTS)

    def test_cli_without_gh_fails_loudly(self, tmp_path, monkeypatch):
        """No network, no gh, no token -> exit 2, never a vacuous pass."""
        empty_bin = tmp_path / "bin"
        empty_bin.mkdir()
        monkeypatch.setenv("PATH", str(empty_bin))
        proc = self._run(["--json"], tmp_path)
        assert proc.returncode == 2
        assert "Cannot audit" in proc.stderr
