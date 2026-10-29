"""Tests for the CI trigger coverage audit (v13 DoD #7).

The invariant under test is simple to state and easy to break by accident:

    **Every pull request must be verified by CI, whatever branch it
    targets.**

A workflow whose ``on.pull_request`` block carries a ``branches:`` filter
runs only for pull requests whose base branch matches that filter.  When
the filter names just ``master``, a *stacked* pull request -- one whose
base is another feature branch -- never starts the workflow at all.  The
pull request then shows an **empty** check list, which is easy to mistake
for "still running", and its code lands unverified.

This repository hit exactly that: PR #63 (base ``feat/v13-replay-provenance``)
recorded no CI run whatsoever, while PRs #60/#61/#62 (base ``master``) each
received the full 6-job suite.

These tests pin two things:

1. the *parser* behaves correctly on the workflow shapes that matter, and
2. the *repository's own* workflows currently satisfy the invariant.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from ci_trigger_audit import (  # noqa: E402
    MAINLINE_BRANCHES,
    WorkflowParseError,
    audit_all,
    audit_workflow,
    branch_matches,
    find_uncovered_bases,
)

CI_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "ci.yml"


# ── Helpers ─────────────────────────────────────────────────────────────────

def _write_workflow(tmp_path: Path, body: str) -> Path:
    path = tmp_path / "wf.yml"
    path.write_text(body, encoding="utf-8")
    return path


# ── The repository's own invariant ──────────────────────────────────────────

class TestRepositoryInvariant:
    """The live repository must satisfy the invariant, right now."""

    def test_ci_workflow_has_no_pull_request_branches_filter(self):
        """The single most important assertion.

        If this fails, stacked pull requests silently lose CI again.
        """
        audit = audit_workflow(CI_WORKFLOW)
        assert audit.has_pull_request, "CI workflow must subscribe to pull_request"
        assert audit.branches is None, (
            "CI workflow's pull_request trigger must NOT be narrowed by a "
            f"'branches:' filter (found: {audit.branches}). A filter means "
            "stacked pull requests (base = another feature branch) get "
            "zero CI checks."
        )

    def test_ci_workflow_covers_every_base_branch(self):
        audit = audit_workflow(CI_WORKFLOW)
        assert audit.is_unfiltered
        for base in ("master", "main", "feat/v13-replay-provenance"):
            assert audit.covers(base), f"base {base} must be covered"

    def test_no_workflow_leaves_a_base_branch_uncovered(self):
        """Every workflow that runs on pull requests covers every base."""
        audits = audit_all()
        pull_request_workflows = [a for a in audits if a.has_pull_request]
        assert pull_request_workflows, "expected at least one PR workflow"

        bases = list(MAINLINE_BRANCHES) + [
            "feat/v12-sdk-foundation",
            "feat/v13-provenance-provenance",
            "feat/v13-replay-provenance",
            "feat/v13-replay-integrity-guard",
        ]
        gaps = find_uncovered_bases(audits, bases)
        assert gaps == [], f"uncovered (workflow, base) pairs: {gaps}"

    def test_audit_script_exits_zero_on_repository(self):
        """The script must be usable as a CI gate (exit 0 == no gaps)."""
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "ci_trigger_audit.py")],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, (
            f"ci_trigger_audit.py reported gaps:\n{result.stdout}\n{result.stderr}"
        )


# ── Parser behaviour ────────────────────────────────────────────────────────

class TestTriggerParsing:
    def test_flow_list_filter_is_parsed(self, tmp_path):
        wf = _write_workflow(tmp_path, """
name: CI

on:
  push:
    branches: [master, daily/*]
  pull_request:
    branches: [master]
""")
        audit = audit_workflow(wf)
        assert audit.branches == ["master"]
        assert audit.covers("master")
        assert not audit.covers("feat/anything")

    def test_block_list_filter_is_parsed(self, tmp_path):
        wf = _write_workflow(tmp_path, """
name: CI

on:
  pull_request:
    branches:
      - master
      - release/*
""")
        audit = audit_workflow(wf)
        assert audit.branches == ["master", "release/*"]

    def test_absent_filter_means_unfiltered(self, tmp_path):
        wf = _write_workflow(tmp_path, """
name: CI

on:
  pull_request:
  push:
    branches: [master]
""")
        audit = audit_workflow(wf)
        assert audit.branches is None
        assert audit.is_unfiltered
        assert audit.covers("anything-at-all")

    def test_comments_are_not_mistaken_for_events(self, tmp_path):
        """Regression guard: a comment inside 'on:' is not an event name.

        This bit us for real: the explanatory comment added next to the
        fix was parsed as a list of 'events', which made the audit report
        nonsense.
        """
        wf = _write_workflow(tmp_path, """
name: CI

on:
  # A comment describing the trigger.
  # Another comment line.
  push:
    branches: [master]
  pull_request:
""")
        audit = audit_workflow(wf)
        assert audit.events == ["push", "pull_request"]

    def test_inline_comment_on_event_line_is_ignored(self, tmp_path):
        wf = _write_workflow(tmp_path, """
name: CI

on:
  push:  # only the mainline
    branches: [master]
  pull_request:
""")
        audit = audit_workflow(wf)
        assert audit.events == ["push", "pull_request"]

    def test_missing_on_block_raises(self, tmp_path):
        wf = _write_workflow(tmp_path, "name: CI\n\njobs: {}\n")
        with pytest.raises(WorkflowParseError):
            audit_workflow(wf)

    def test_release_workflow_has_no_pull_request(self):
        """release.yml is tag-driven; it must not be counted as a gap."""
        audits = audit_all()
        release = [a for a in audits if a.workflow.name == "release.yml"]
        assert release, "release.yml should exist"
        assert not release[0].has_pull_request
        # And it must not produce a false gap.
        gaps = find_uncovered_bases(audits, ["master"])
        assert all("release.yml" not in w for w, _ in gaps)


# ── GitHub filter pattern semantics ─────────────────────────────────────────

class TestBranchMatching:
    def test_exact_match(self):
        assert branch_matches("master", ["master"])
        assert not branch_matches("masterx", ["master"])

    def test_single_star_does_not_cross_slash(self):
        """GitHub's '*' matches within a path segment, not across '/'. """
        assert branch_matches("daily/2026-01-01", ["daily/*"])
        assert not branch_matches("daily/2026/01", ["daily/*"])

    def test_double_star_crosses_slash(self):
        assert branch_matches("feat/a/b", ["feat/**"])
        assert branch_matches("feat/a", ["feat/**"])

    def test_question_mark_matches_single_char(self):
        assert branch_matches("v1", ["v?"])
        assert not branch_matches("v12", ["v?"])

    def test_empty_filter_matches_nothing(self):
        assert not branch_matches("master", [])


# ── CLI surface ─────────────────────────────────────────────────────────────

class TestCli:
    def test_json_output_is_machine_readable(self):
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "ci_trigger_audit.py"), "--json"],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["ok"] is True
        assert payload["gaps"] == []
        assert any(w["workflow"].endswith("ci.yml") for w in payload["workflows"])

    def test_explicit_base_option(self):
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "ci_trigger_audit.py"),
                "--base",
                "feat/v13-replay-provenance",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0, result.stderr
        payload = json.loads(result.stdout)
        assert payload["probed_base_branches"] == ["feat/v13-replay-provenance"]
        assert payload["ok"] is True

    def test_detects_gap_when_filter_narrows(self, tmp_path):
        """The audit must FAIL when a stacked base is uncovered."""
        wf = _write_workflow(tmp_path, """
name: CI

on:
  pull_request:
    branches: [master]
""")
        result = subprocess.run(
            [
                sys.executable,
                str(REPO_ROOT / "scripts" / "ci_trigger_audit.py"),
                "--workflow",
                str(wf),
                "--base",
                "feat/stacked",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1, "audit should fail on an uncovered base"
        payload = json.loads(result.stdout)
        assert payload["ok"] is False
        assert payload["gaps"] == [
            {"workflow": str(wf), "base_branch": "feat/stacked"}
        ]
