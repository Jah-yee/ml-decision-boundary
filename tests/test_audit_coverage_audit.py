"""Tests for the audit coverage audit (v14 DoD #19).

The invariant under test is a **meta**-invariant -- one level above
every other audit in this repository:

    **An audit that runs green while narrowly scoped produces exactly
    the wrong signal.  It says "this area is verified" when the truth
    is "this area was never looked at".**

Every other audit in this repository answers a question *about an
artifact*: would this workflow trigger, is this pull request covered,
is the job graph sound, is the release pipeline safe.  This audit
answers a question *about the audits themselves*: **when an audit job
runs, which artifacts does it actually examine?**

**The concrete defect this audit exists for.**

``.github/workflows/ci.yml`` contains the job ``release-audit``, which
used to run::

    python3 scripts/release_audit.py --workflow .github/workflows/release.yml --strict

The ``--workflow`` argument narrows the audit to a **single file**.
The repository has **two** workflow files, so this job audited
``release.yml`` and never audited ``ci.yml`` -- the workflow that
holds eleven jobs, the pull-request gate and the token permissions.

Measured on 2026-11-07: removing the ``permissions:`` block from
``ci.yml`` left **every** audit in the repository exiting 0::

    release_audit --workflow .github/workflows/release.yml --strict  exit 0
    ci_trigger_audit.py                                             exit 0
    job_graph_audit.py                                              exit 0

The auditor was capable of catching the defect; the *invocation* never
pointed it at the file.  So the previous round's fix -- adding
``permissions: contents: read`` to ``ci.yml`` -- had **no guard**: a
future regression lands green.

**What these tests pin.**

1. the *parser* -- the workflow subset reader, including block scalars
   (``run: |``) and the ``- name:``/``run:`` step shape;
2. the *detections* -- a narrowed invocation and an uncovered
   workflow;
3. the *monotonicity* -- the strict mode must be a strict superset of
   the default mode and must never be laxer;
4. the *false-positive guard* -- scripts that do not audit workflow
   files (``pr_coverage_audit.py``) must not be reported;
5. the *bug injection* -- the original defect must actually be caught
   by the shipped tests, not merely described by them.

Every test writes its own throwaway workflow file.  A test that
depends on the ambient repository measures the environment, not the
code.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT_PATH = REPO_ROOT / "scripts" / "audit_coverage_audit.py"

_spec = importlib.util.spec_from_file_location("audit_coverage_audit", SCRIPT_PATH)
assert _spec and _spec.loader
mod = importlib.util.module_from_spec(_spec)
sys.modules["audit_coverage_audit"] = mod
_spec.loader.exec_module(mod)


# ── fixtures / helpers ─────────────────────────────────────────────────────

MINIMAL_CI = """\
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  an-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit
        run: python3 scripts/ci_trigger_audit.py
"""

#: The exact shape of the defect: an audit invocation narrowed to one
#: workflow file while a second workflow file exists.
NARROWED_CI = """\
name: CI

on:
  push:
  pull_request:

permissions:
  contents: read

jobs:
  release-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit release pipeline
        run: python3 scripts/release_audit.py --workflow .github/workflows/release.yml --strict
"""


def _write_workflow(directory: Path, name: str, text: str) -> Path:
    path = directory / name
    path.write_text(text, encoding="utf-8")
    return path


def _two_workflow_dir(tmp_path: Path) -> Path:
    """A workflow directory with ``ci.yml`` and ``release.yml``."""
    directory = tmp_path / "workflows"
    directory.mkdir()
    _write_workflow(directory, "ci.yml", NARROWED_CI)
    _write_workflow(
        directory,
        "release.yml",
        "name: Release\n\non:\n  push:\n    tags: ['v*']\n\njobs:\n  release:\n"
        "    runs-on: ubuntu-latest\n    steps:\n      - run: echo hi\n",
    )
    return directory


# ── 1. the parser ──────────────────────────────────────────────────────────


class TestParser:
    """The workflow subset reader."""

    def test_finds_job_names(self, tmp_path: Path) -> None:
        path = _write_workflow(tmp_path, "ci.yml", MINIMAL_CI)
        workflow = mod.parse_workflow(path)
        assert "an-audit" in workflow.jobs

    def test_finds_inline_run_step(self, tmp_path: Path) -> None:
        text = MINIMAL_CI.replace(
            "      - name: Audit\n        run: python3 scripts/ci_trigger_audit.py\n",
            "      - run: python3 scripts/ci_trigger_audit.py\n",
        )
        path = _write_workflow(tmp_path, "ci.yml", text)
        workflow = mod.parse_workflow(path)
        assert any(
            "ci_trigger_audit.py" in run
            for run in workflow.jobs["an-audit"].run_scripts
        )

    def test_finds_block_scalar_run_step(self, tmp_path: Path) -> None:
        """A ``run: |`` block must be folded into one command.

        Every multi-line CI step in this repository is written this
        way, so a reader that only understands ``- run: <one line>``
        would find *nothing*.
        """
        text = """\
name: CI

on:
  push:

jobs:
  an-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit
        run: |
          echo preparing
          python3 scripts/release_audit.py --strict
          echo done
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        workflow = mod.parse_workflow(path)
        runs = workflow.jobs["an-audit"].run_scripts
        assert len(runs) == 1
        assert "release_audit.py" in runs[0]
        assert "echo preparing" in runs[0]
        assert "echo done" in runs[0]

    def test_block_scalar_ends_at_dedent(self, tmp_path: Path) -> None:
        """The next step must not be swallowed by the previous block."""
        text = """\
name: CI

on:
  push:

jobs:
  first:
    runs-on: ubuntu-latest
    steps:
      - name: One
        run: |
          python3 scripts/release_audit.py --strict
  second:
    runs-on: ubuntu-latest
    steps:
      - name: Two
        run: python3 scripts/ci_trigger_audit.py
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        workflow = mod.parse_workflow(path)
        assert len(workflow.jobs) == 2
        assert len(workflow.jobs["first"].run_scripts) == 1
        assert len(workflow.jobs["second"].run_scripts) == 1

    def test_ignores_jobs_outside_workflow(self, tmp_path: Path) -> None:
        """A ``run:`` before the ``jobs:`` key is not a job step."""
        text = """\
name: CI

on:
  push:
    tags: ['v*']

permissions:
  contents: write

jobs:
  an-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit
        run: python3 scripts/release_audit.py --strict
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        workflow = mod.parse_workflow(path)
        assert len(workflow.jobs) == 1

    def test_comments_are_stripped(self, tmp_path: Path) -> None:
        """A commented-out invocation must not be counted."""
        text = """\
name: CI

on:
  push:

jobs:
  an-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit
        # run: python3 scripts/release_audit.py --workflow x.yml
        run: python3 scripts/ci_trigger_audit.py
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        workflow = mod.parse_workflow(path)
        runs = workflow.jobs["an-audit"].run_scripts
        assert len(runs) == 1
        assert "release_audit.py" not in runs[0]

    def test_missing_file_raises(self, tmp_path: Path) -> None:
        with pytest.raises(mod.AuditCoverageError):
            mod.parse_workflow(tmp_path / "nope.yml")


# ── 2. invocation discovery ────────────────────────────────────────────────


class TestInvocationDiscovery:
    """Which audit invocations exist, and what do they cover."""

    def test_finds_audit_invocations(self, tmp_path: Path) -> None:
        path = _write_workflow(tmp_path, "ci.yml", MINIMAL_CI)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert len(invocations) == 1
        assert invocations[0].script == "ci_trigger_audit.py"
        assert invocations[0].job == "an-audit"

    def test_records_explicit_workflow_paths(self, tmp_path: Path) -> None:
        path = _write_workflow(tmp_path, "ci.yml", NARROWED_CI)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert invocations[0].explicit_paths == [".github/workflows/release.yml"]
        assert invocations[0].is_narrowed is True

    def test_ignores_unknown_scripts(self, tmp_path: Path) -> None:
        """A script that is not a known audit is not an invocation.

        Otherwise every ``python3 scripts/foo.py`` in CI would be
        treated as a workflow audit.
        """
        text = MINIMAL_CI.replace(
            "python3 scripts/ci_trigger_audit.py", "python3 scripts/generate_changelog.py"
        )
        path = _write_workflow(tmp_path, "ci.yml", text)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert invocations == []

    def test_ignores_pr_coverage_audit(self, tmp_path: Path) -> None:
        """``pr_coverage_audit.py`` audits pull requests, not workflows.

        Reporting it as a narrowed workflow audit would be a false
        positive -- and false positives are not merely noise: they
        hide the real defect among the fake alarms.
        """
        text = MINIMAL_CI.replace(
            "python3 scripts/ci_trigger_audit.py",
            "python3 scripts/pr_coverage_audit.py --workflow x.yml",
        )
        path = _write_workflow(tmp_path, "ci.yml", text)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert invocations == []

    def test_multiple_invocations_in_one_job(self, tmp_path: Path) -> None:
        text = """\
name: CI

on:
  push:

jobs:
  multi:
    runs-on: ubuntu-latest
    steps:
      - name: One
        run: python3 scripts/ci_trigger_audit.py
      - name: Two
        run: python3 scripts/job_graph_audit.py
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert {i.script for i in invocations} == {
            "ci_trigger_audit.py",
            "job_graph_audit.py",
        }


# ── 3. the detections ──────────────────────────────────────────────────────


class TestCoverageDetection:
    """The two defects this audit detects."""

    def test_detects_narrowed_invocation(self, tmp_path: Path) -> None:
        """The original defect: one file audited out of two.

        Two things are true at once here, and both are reported:

        * the invocation is **narrowed** -- it names one file out of
          two, so it is a narrowing of what the audit could have
          covered;
        * ``ci.yml`` ends up **completely uncovered** -- no invocation
          at all examines it.

        The second is the one that matters for the security story:
        ``ci.yml`` is the workflow holding the pull-request gate and
        the token permissions.
        """
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        assert result["ok"] is False
        problems = result["problems"]
        by_check = {p["check"]: p for p in problems}
        assert "coverage_narrowed" in by_check
        narrowed = by_check["coverage_narrowed"]
        assert narrowed["script"] == "release_audit.py"
        assert narrowed["misses"] == ["ci.yml"]
        assert "workflow_uncovered" in by_check
        assert by_check["workflow_uncovered"]["workflow_file"] == "ci.yml"

    def test_unnarrowed_invocation_passes(self, tmp_path: Path) -> None:
        directory = _two_workflow_dir(tmp_path)
        path = directory / "ci.yml"
        path.write_text(
            MINIMAL_CI.replace(
                "python3 scripts/ci_trigger_audit.py", "python3 scripts/release_audit.py --strict"
            ),
            encoding="utf-8",
        )
        result = mod.audit_repo(workflow_dir=directory)
        assert result["ok"] is True
        assert result["problems"] == []

    def test_detects_uncovered_workflow(self, tmp_path: Path) -> None:
        """A workflow no invocation examines at all."""
        directory = _two_workflow_dir(tmp_path)
        path = directory / "ci.yml"
        path.write_text(
            MINIMAL_CI.replace(
                "python3 scripts/ci_trigger_audit.py", "python3 scripts/unrelated_thing.py"
            ),
            encoding="utf-8",
        )
        result = mod.audit_repo(workflow_dir=directory)
        assert result["ok"] is False
        checks = {p["check"] for p in result["problems"]}
        assert "workflow_uncovered" in checks
        assert result["uncovered"] == ["ci.yml", "release.yml"]

    def test_narrowed_to_everything_is_not_a_coverage_defect(self) -> None:
        """Naming *every* workflow is not narrowing.

        The default gate must not fail on it -- only the strict gate
        forbids narrowing as a matter of policy.
        """
        invocations = [
            mod.Invocation(
                script="release_audit.py",
                job="release-audit",
                workflow_file="ci.yml",
                command="python3 scripts/release_audit.py --workflow a.yml --workflow b.yml",
                explicit_paths=["a.yml", "b.yml"],
            )
        ]
        result = mod.check_coverage(invocations, ["a.yml", "b.yml"])
        assert result["ok"] is True
        assert result["problems"] == []

    def test_covers_reports_each_invocation(self, tmp_path: Path) -> None:
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        entry = result["invocations"][0]
        assert entry["covers"] == ["release.yml"]
        assert entry["misses"] == ["ci.yml"]


# ── 4. gate monotonicity ───────────────────────────────────────────────────


class TestGateMonotonicity:
    """The strict mode must be a strict superset of the default mode."""

    def test_default_requirements_are_a_subset(self) -> None:
        assert set(mod.DEFAULT_REQUIREMENTS) < set(mod.STRICT_REQUIREMENTS)

    def test_strict_fails_where_default_passes(self, tmp_path: Path) -> None:
        """A narrowing that covers everything: default passes, strict fails.

        This is the difference between the two modes.  If strict did
        not fail here, the strict mode would add nothing.
        """
        invocations = [
            mod.Invocation(
                script="release_audit.py",
                job="release-audit",
                workflow_file="ci.yml",
                command="python3 scripts/release_audit.py --workflow a.yml",
                explicit_paths=["a.yml"],
            )
        ]
        result = mod.check_coverage(invocations, ["a.yml"])
        default_gate = mod.evaluate_gate(result, strict=False)
        strict_gate = mod.evaluate_gate(result, strict=True)
        assert default_gate["ok"] is True
        assert strict_gate["ok"] is False
        assert strict_gate["failed"] == [mod.STRICT_REQUIREMENT]

    def test_default_fails_on_any_problem(self, tmp_path: Path) -> None:
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        gate = mod.evaluate_gate(result, strict=False)
        assert gate["ok"] is False
        assert mod.DEFAULT_REQUIREMENT in gate["failed"]

    def test_strict_is_never_laxer_than_default(self, tmp_path: Path) -> None:
        """For every input, strict fails whenever default fails.

        This is the property the other gates in this repository are
        built on: a stricter gate can only ever turn a pass into a
        failure, never the other way round.
        """
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        default_gate = mod.evaluate_gate(result, strict=False)
        strict_gate = mod.evaluate_gate(result, strict=True)
        if not default_gate["ok"]:
            assert not strict_gate["ok"]

    def test_unknown_requirement_raises(self) -> None:
        result = {"problems": []}
        with pytest.raises(ValueError):
            mod._requirement_failed(result, "not_a_requirement")


# ── 5. the CLI ─────────────────────────────────────────────────────────────


class TestCli:
    """The command-line interface."""

    def test_exit_code_on_failure(self, tmp_path: Path) -> None:
        directory = _two_workflow_dir(tmp_path)
        assert mod.main(["--workflow-dir", str(directory)]) == 1

    def test_exit_code_on_success(self, tmp_path: Path) -> None:
        directory = _two_workflow_dir(tmp_path)
        path = directory / "ci.yml"
        path.write_text(
            MINIMAL_CI.replace(
                "python3 scripts/ci_trigger_audit.py", "python3 scripts/release_audit.py --strict"
            ),
            encoding="utf-8",
        )
        assert mod.main(["--workflow-dir", str(directory)]) == 0

    def test_json_output_is_machine_readable(self, tmp_path: Path) -> None:
        import json

        directory = _two_workflow_dir(tmp_path)
        assert mod.main(["--workflow-dir", str(directory), "--json"]) == 1

    def test_missing_workflow_dir_exits_two(self, tmp_path: Path) -> None:
        assert mod.main(["--workflow-dir", str(tmp_path / "nope")]) == 2

    def test_missing_ci_workflow_exits_two(self, tmp_path: Path) -> None:
        directory = tmp_path / "workflows"
        directory.mkdir()
        assert mod.main(["--workflow-dir", str(directory)]) == 2


# ── 6. bug injection ───────────────────────────────────────────────────────


class TestBugInjection:
    """The shipped tests must actually catch the defect they describe.

    A test that asserts a defect is detected, but which would still
    pass with the detection removed, is documentation -- not a test.
    These tests re-introduce the defect and require a failure.
    """

    def test_detection_is_real_when_narrowing_is_present(self, tmp_path: Path) -> None:
        """The narrowed invocation must be caught, not merely described."""
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        # If the detection were removed, this list would be empty.
        assert any(p["check"] == "coverage_narrowed" for p in result["problems"])

    def test_coverage_actually_misses_a_workflow(self, tmp_path: Path) -> None:
        """The narrowed invocation must really skip a file.

        This is the *behavioural* half of the injection: it does not
        trust the auditor's own report, it checks that the reported
        miss is the file that the invocation genuinely does not name.
        """
        directory = _two_workflow_dir(tmp_path)
        result = mod.audit_repo(workflow_dir=directory)
        invocation = result["invocations"][0]
        # The invocation names release.yml only, and ci.yml exists.
        assert invocation["explicit_paths"] == [".github/workflows/release.yml"]
        assert "ci.yml" in invocation["misses"]
        assert (directory / "ci.yml").exists()

    def test_parser_regression_is_caught(self, tmp_path: Path) -> None:
        """If block-scalar parsing broke, the audit would go blind.

        A parser that cannot read ``run: |`` would find zero
        invocations and report every workflow as uncovered -- which is
        a different, loud failure.  This test pins the parser
        behaviour directly.
        """
        text = """\
name: CI

on:
  push:

jobs:
  an-audit:
    runs-on: ubuntu-latest
    steps:
      - name: Audit
        run: |
          python3 scripts/release_audit.py --strict
"""
        path = _write_workflow(tmp_path, "ci.yml", text)
        invocations = mod.discover_invocations(mod.parse_workflow(path))
        assert len(invocations) == 1


# ── 7. the real repository ─────────────────────────────────────────────────


class TestRealRepository:
    """The invariant, checked against the repository as it stands."""

    def test_every_audit_invocation_covers_every_workflow(self) -> None:
        """No audit job may be narrowed below the workflow set.

        This is the invariant the CI job ``audit-coverage-audit``
        enforces.  If it fails here, the repository has reintroduced
        the defect this audit was written for.
        """
        result = mod.audit_repo()
        assert result["ok"] is True, result["problems"]

    def test_the_release_audit_job_is_not_narrowed(self) -> None:
        """The specific regression this round fixed.

        The check reads the *command* of every step, not the raw file
        text: the workflow carries a comment explaining the old
        defect, and that explanation necessarily quotes the old
        command.
        """
        ci_path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        workflow = mod.parse_workflow(ci_path)
        invocations = mod.discover_invocations(workflow)
        release_invocations = [i for i in invocations if i.script == "release_audit.py"]
        assert release_invocations, "the release audit job disappeared"
        for invocation in release_invocations:
            assert invocation.explicit_paths == []
            assert invocation.is_narrowed is False
