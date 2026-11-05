"""Tests for the CI job dependency graph audit (v13 DoD #18).

The invariant under test is the *inside-the-workflow* counterpart of the
ones introduced earlier:

    **Every verification job must actually be waited for by the gate
    that certifies the pull request.**

DoD #7 fixed the workflow trigger block ("would CI even start?").
DoD #8 added a pull-request-level audit of CI coverage ("is every pull
request verified?").  DoD #16 made the two gate modes monotonic.
DoD #17 audited the *shape* of the branch stack.

None of them look **inside** the ``jobs:`` block.  A workflow can have a
perfect ``on:`` trigger, every open pull request can be fully covered,
the stack can be perfectly linear — and the workflow can still be
structurally broken in a way that makes the green CI mean nothing.

**The three concrete defects.**

1. **A dangling ``needs:`` target kills the whole workflow.**  If a job
   names a ``needs:`` target that does not exist, GitHub rejects the
   **entire workflow** — not just the offending job.  Every real quality
   job is skipped along with it.  A one-character typo therefore turns a
   green CI into a CI that verifies *nothing*.
2. **A ``needs:`` cycle makes jobs silently never run.**  A job that
   transitively depends on itself is dropped from the execution order.
3. **An ungated job makes the gate lie.**  If a new verification job is
   added and the gate's ``needs:`` list is not updated, the gate reports
   "this pull request is fully verified" while the new job — which may
   have failed — never contributed to the verdict.

The third defect is the reason this is a *gate* and not a lint, and it is
the exact analogue of the DoD #16 finding: **a gate that does not fail
on the defect it exists to catch is not a gate, it is a rubber stamp.**

**What these tests pin.**

1. the *parser* — the workflow subset reader, including its refusal to
   guess on malformed input;
2. the *classification* — which jobs are gates, which are verifications,
   and which are aggregating gates;
3. the *four detections* — dangling needs, self dependency, cycles,
   ungated jobs;
4. the *monotonicity* — the strict mode must be a strict superset of the
   default mode and must never be laxer;
5. the *bug injection* — the original defect must actually be caught by
   the shipped tests, not merely described by them.

Every test writes its own throwaway workflow file.  A test that depends
on the ambient repository measures the environment, not the code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from job_graph_audit import (  # noqa: E402
    DEFAULT_REQUIREMENTS,
    STRICT_REQUIREMENTS,
    WorkflowParseError,
    add_reachability,
    audit_workflow,
    evaluate_gate,
    find_cycles,
    is_gate_job,
    is_verification_job,
    parse_workflow,
)


# ── helpers ────────────────────────────────────────────────────────────────


def _write_workflow(tmp_path: Path, body: str, name: str = "ci.yml") -> Path:
    """Write a throwaway workflow file and return its path."""
    path = tmp_path / name
    path.write_text(body, encoding="utf-8")
    return path


def _workflow(jobs: str) -> str:
    """Wrap a ``jobs:`` body in a minimal valid workflow."""
    return f"name: CI\n\non:\n  push:\n\njobs:\n{jobs}"


def _audit(tmp_path: Path, jobs: str):
    """Parse and audit a throwaway workflow; return the audit result."""
    path = _write_workflow(tmp_path, _workflow(jobs))
    workflow = parse_workflow(path)
    result = audit_workflow(workflow)
    add_reachability(result, workflow)
    return result


def _simple_jobs() -> str:
    return """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: python3 scripts/pr_coverage_audit.py
"""


# ── the parser ─────────────────────────────────────────────────────────────


class TestParser:
    def test_a_minimal_workflow_is_parsed(self, tmp_path):
        path = _write_workflow(tmp_path, _workflow(_simple_jobs()))
        workflow = parse_workflow(path)
        assert set(workflow.jobs) == {"quality-gates", "pr-coverage-gate"}

    def test_an_inline_needs_list_is_parsed(self, tmp_path):
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(_simple_jobs())))
        assert workflow.jobs["pr-coverage-gate"].needs == ["quality-gates"]

    def test_a_block_needs_list_is_parsed(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs:
      - a
    steps:
      - run: echo b
"""
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(jobs)))
        assert workflow.jobs["b"].needs == ["a"]

    def test_a_scalar_needs_is_parsed(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: a
    steps:
      - run: echo b
"""
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(jobs)))
        assert workflow.jobs["b"].needs == ["a"]

    def test_a_job_without_needs_has_an_empty_list(self, tmp_path):
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(_simple_jobs())))
        assert workflow.jobs["quality-gates"].needs == []

    def test_a_run_step_is_detected(self, tmp_path):
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(_simple_jobs())))
        assert workflow.jobs["quality-gates"].has_run is True

    def test_a_job_with_only_uses_steps_has_no_run(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
"""
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(jobs)))
        assert workflow.jobs["a"].has_run is False
        assert workflow.jobs["a"].has_steps is True

    def test_a_workflow_without_a_jobs_block_raises(self, tmp_path):
        path = _write_workflow(tmp_path, "name: CI\non:\n  push:\n")
        with pytest.raises(WorkflowParseError):
            parse_workflow(path)

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(WorkflowParseError):
            parse_workflow(tmp_path / "does-not-exist.yml")

    def test_a_commented_needs_is_not_treated_as_a_dependency(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs:
      # - commented-out
      - a
    steps:
      - run: echo b
"""
        workflow = parse_workflow(_write_workflow(tmp_path, _workflow(jobs)))
        assert workflow.jobs["b"].needs == ["a"]


# ── the classification ─────────────────────────────────────────────────────


class TestClassification:
    def test_a_gate_suffixed_job_is_a_gate(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert "pr-coverage-gate" in result["gates"]

    def test_an_audit_suffixed_job_is_a_gate(self, tmp_path):
        jobs = """  ci-trigger-audit:
    runs-on: ubuntu-latest
    steps:
      - run: python3 scripts/ci_trigger_audit.py
"""
        result = _audit(tmp_path, jobs)
        assert "ci-trigger-audit" in result["gates"]

    def test_an_audit_job_without_needs_is_still_a_gate(self, tmp_path):
        """A standalone audit fails the build on its own.

        It must not be classified as a verification job, or the gate
        would be required to wait for an audit that gates nothing.
        """
        jobs = """  ci-trigger-audit:
    runs-on: ubuntu-latest
    steps:
      - run: python3 scripts/ci_trigger_audit.py
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
"""
        result = _audit(tmp_path, jobs)
        assert "ci-trigger-audit" in result["gates"]
        assert "ci-trigger-audit" not in result["verifications"]

    def test_a_job_with_a_run_step_is_a_verification_job(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert "quality-gates" in result["verifications"]

    def test_a_gate_is_not_a_verification_job(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert "pr-coverage-gate" not in result["verifications"]

    def test_a_gate_with_needs_is_an_aggregating_gate(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert result["aggregating_gates"] == ["pr-coverage-gate"]

    def test_a_standalone_audit_is_not_an_aggregating_gate(self, tmp_path):
        jobs = """  ci-trigger-audit:
    runs-on: ubuntu-latest
    steps:
      - run: python3 scripts/ci_trigger_audit.py
"""
        result = _audit(tmp_path, jobs)
        assert result["aggregating_gates"] == []


# ── detection 1: dangling needs ────────────────────────────────────────────


class TestDanglingNeeds:
    def test_a_dangling_needs_target_is_detected(self, tmp_path):
        jobs = """  gate:
    runs-on: ubuntu-latest
    needs: [nonexistent_job]
    steps:
      - run: echo hi
"""
        result = _audit(tmp_path, jobs)
        assert result["dangling_needs"] == [
            {"job": "gate", "needs": "nonexistent_job"}
        ]
        assert result["ok"] is False

    def test_the_problem_message_explains_the_blast_radius(self, tmp_path):
        """A dangling needs target takes the WHOLE workflow down.

        The message must say so, otherwise the reader assumes only the
        offending job is affected — which is exactly the wrong
        conclusion, and would lead to "I'll fix it in the next PR".
        """
        jobs = """  gate:
    runs-on: ubuntu-latest
    needs: [nonexistent_job]
    steps:
      - run: echo hi
"""
        result = _audit(tmp_path, jobs)
        assert any("ENTIRE workflow" in p for p in result["problems"])

    def test_a_valid_needs_target_is_not_reported(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert result["dangling_needs"] == []


# ── detection 2: self dependency ───────────────────────────────────────────


class TestSelfDependency:
    def test_a_self_dependency_is_detected(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo hi
"""
        result = _audit(tmp_path, jobs)
        assert result["self_dependencies"] == ["a"]
        assert result["ok"] is False

    def test_a_normal_dependency_is_not_a_self_dependency(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert result["self_dependencies"] == []


# ── detection 3: cycles ────────────────────────────────────────────────────


class TestCycles:
    def test_a_two_node_cycle_is_detected(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    needs: [b]
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo b
"""
        result = _audit(tmp_path, jobs)
        assert result["cycles"]
        assert result["ok"] is False

    def test_the_cycle_path_is_reported(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    needs: [b]
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo b
"""
        result = _audit(tmp_path, jobs)
        cycle = result["cycles"][0]
        assert cycle[0] == cycle[-1]

    def test_an_acyclic_graph_reports_no_cycles(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo b
  c:
    runs-on: ubuntu-latest
    needs: [b]
    steps:
      - run: echo c
"""
        result = _audit(tmp_path, jobs)
        assert result["cycles"] == []

    def test_a_diamond_is_not_a_cycle(self, tmp_path):
        """A diamond is acyclic even though there are two paths."""
        jobs = """  a:
    runs-on: ubuntu-latest
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo b
  c:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo c
  d:
    runs-on: ubuntu-latest
    needs: [b, c]
    steps:
      - run: echo d
"""
        result = _audit(tmp_path, jobs)
        assert result["cycles"] == []

    def test_find_cycles_ignores_dangling_targets(self, tmp_path):
        """A dangling target is a different defect; it must not also
        be reported as a cycle."""
        workflow = parse_workflow(
            _write_workflow(
                tmp_path,
                _workflow(
                    """  a:
    runs-on: ubuntu-latest
    needs: [missing]
    steps:
      - run: echo a
"""
                ),
            )
        )
        assert find_cycles(workflow.jobs) == []


# ── detection 4: ungated jobs ──────────────────────────────────────────────


class TestGateCoverage:
    def test_a_verification_job_missing_from_the_gate_is_detected(self, tmp_path):
        """The headline defect: the gate would certify unverified code."""
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  brand-new-check:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q tests/new.py
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: python3 scripts/pr_coverage_audit.py
"""
        result = _audit(tmp_path, jobs)
        assert result["ungated_jobs"] == [
            {"gate": "pr-coverage-gate", "job": "brand-new-check"}
        ]
        assert result["ok"] is False

    def test_the_problem_message_says_the_gate_would_lie(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  brand-new-check:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q tests/new.py
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: python3 scripts/pr_coverage_audit.py
"""
        result = _audit(tmp_path, jobs)
        assert any("would report 'verified' without it" in p for p in result["problems"])

    def test_a_fully_covered_gate_is_not_reported(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert result["ungated_jobs"] == []

    def test_a_standalone_audit_is_not_required_to_cover_anything(self, tmp_path):
        """An audit with no needs: has nothing to aggregate."""
        jobs = """  ci-trigger-audit:
    runs-on: ubuntu-latest
    steps:
      - run: python3 scripts/ci_trigger_audit.py
  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
"""
        result = _audit(tmp_path, jobs)
        assert result["ungated_jobs"] == []
        assert result["ok"] is True

    def test_every_aggregating_gate_must_cover_every_verification_job(self, tmp_path):
        """Two gates: one covers everything, the other covers nothing."""
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - run: python3 main.py
  alpha-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates, benchmark]
    steps:
      - run: echo one
  beta-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo two
"""
        result = _audit(tmp_path, jobs)
        assert result["ungated_jobs"] == [{"gate": "beta-gate", "job": "benchmark"}]


# ── reachability (strict mode) ─────────────────────────────────────────────


class TestReachability:
    def test_a_workflow_with_no_gate_has_no_unreachable_jobs(self, tmp_path):
        """A standalone pipeline (e.g. release.yml) has no gate.

        Reporting its jobs as unreachable would be a false positive, and
        a gate that cries wolf is a gate that gets ignored.
        """
        jobs = """  release:
    runs-on: ubuntu-latest
    steps:
      - run: echo release
"""
        result = _audit(tmp_path, jobs)
        assert result["unreachable_jobs"] == []
        assert result["gate_present"] is False

    def test_a_job_reachable_from_the_gate_is_not_unreachable(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        assert result["unreachable_jobs"] == []

    def test_a_job_outside_the_gate_is_unreachable(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
  orphan:
    runs-on: ubuntu-latest
    steps:
      - run: echo orphan
"""
        result = _audit(tmp_path, jobs)
        assert "orphan" in result["unreachable_jobs"]


# ── the gate ───────────────────────────────────────────────────────────────


class TestGate:
    def test_a_clean_workflow_passes_the_default_gate(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        gate = evaluate_gate([result])
        assert gate["ok"] is True
        assert gate["failed"] == []

    def test_a_dangling_need_fails_the_default_gate(self, tmp_path):
        jobs = """  gate:
    runs-on: ubuntu-latest
    needs: [missing]
    steps:
      - run: echo hi
"""
        gate = evaluate_gate([_audit(tmp_path, jobs)])
        assert gate["ok"] is False
        assert "no_dangling_needs" in gate["failures"][gate["failed"][0]]

    def test_an_ungated_job_fails_the_default_gate(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  extra:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q tests/extra.py
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
"""
        gate = evaluate_gate([_audit(tmp_path, jobs)])
        assert gate["ok"] is False
        assert "gate_coverage" in gate["failures"][gate["failed"][0]]

    def test_a_cycle_fails_the_default_gate(self, tmp_path):
        jobs = """  a:
    runs-on: ubuntu-latest
    needs: [b]
    steps:
      - run: echo a
  b:
    runs-on: ubuntu-latest
    needs: [a]
    steps:
      - run: echo b
"""
        gate = evaluate_gate([_audit(tmp_path, jobs)])
        assert gate["ok"] is False
        assert "acyclic" in gate["failures"][gate["failed"][0]]

    def test_strict_requirements_are_a_strict_superset(self):
        assert set(DEFAULT_REQUIREMENTS) < set(STRICT_REQUIREMENTS)

    def test_strict_mode_is_never_laxer_than_default(self):
        """The DoD #16 invariant, applied to this audit.

        A stricter mode of the same gate must never be laxer than the
        default mode.
        """
        assert len(STRICT_REQUIREMENTS) > len(DEFAULT_REQUIREMENTS)
        assert set(DEFAULT_REQUIREMENTS).issubset(STRICT_REQUIREMENTS)

    def test_strict_mode_adds_exactly_one_requirement(self):
        assert set(STRICT_REQUIREMENTS) - set(DEFAULT_REQUIREMENTS) == {
            "all_jobs_reachable"
        }

    def test_an_unknown_requirement_raises(self, tmp_path):
        result = _audit(tmp_path, _simple_jobs())
        with pytest.raises(ValueError):
            evaluate_gate([result], ("no_such_requirement",))

    def test_the_gate_reports_which_workflow_failed(self, tmp_path):
        good = _audit(tmp_path, _simple_jobs())
        bad_jobs = """  gate:
    runs-on: ubuntu-latest
    needs: [missing]
    steps:
      - run: echo hi
"""
        bad_path = _write_workflow(tmp_path, _workflow(bad_jobs), name="bad.yml")
        bad = audit_workflow(parse_workflow(bad_path))
        add_reachability(bad, parse_workflow(bad_path))
        gate = evaluate_gate([good, bad])
        assert gate["ok"] is False
        assert len(gate["failed"]) == 1
        assert "bad.yml" in gate["failed"][0]


# ── the CLI ────────────────────────────────────────────────────────────────


class TestCli:
    def _run(self, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(REPO_ROOT / "scripts" / "job_graph_audit.py"), *args],
            capture_output=True,
            text=True,
            cwd=tmp_path,
        )

    def test_a_clean_workflow_exits_zero(self, tmp_path):
        path = _write_workflow(tmp_path, _workflow(_simple_jobs()))
        proc = self._run(tmp_path, "--workflow", str(path))
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_a_broken_workflow_exits_one(self, tmp_path):
        jobs = """  gate:
    runs-on: ubuntu-latest
    needs: [missing]
    steps:
      - run: echo hi
"""
        path = _write_workflow(tmp_path, _workflow(jobs))
        proc = self._run(tmp_path, "--workflow", str(path))
        assert proc.returncode == 1

    def test_a_missing_workflow_exits_two(self, tmp_path):
        proc = self._run(tmp_path, "--workflow", str(tmp_path / "nope.yml"))
        assert proc.returncode == 2

    def test_an_unparseable_workflow_exits_two(self, tmp_path):
        path = _write_workflow(tmp_path, "name: CI\non:\n  push:\n")
        proc = self._run(tmp_path, "--workflow", str(path))
        assert proc.returncode == 2
        assert "jobs" in (proc.stdout + proc.stderr)

    def test_json_output_is_parseable(self, tmp_path):
        path = _write_workflow(tmp_path, _workflow(_simple_jobs()))
        proc = self._run(tmp_path, "--workflow", str(path), "--json")
        assert proc.returncode == 0, proc.stdout + proc.stderr
        payload = json.loads(proc.stdout)
        assert "results" in payload
        assert "gate" in payload

    def test_json_output_reports_the_requirements(self, tmp_path):
        path = _write_workflow(tmp_path, _workflow(_simple_jobs()))
        proc = self._run(tmp_path, "--workflow", str(path), "--json")
        payload = json.loads(proc.stdout)
        assert payload["gate"]["requirements"] == list(DEFAULT_REQUIREMENTS)

    def test_strict_mode_adds_a_requirement(self, tmp_path):
        path = _write_workflow(tmp_path, _workflow(_simple_jobs()))
        proc = self._run(tmp_path, "--workflow", str(path), "--json", "--strict")
        payload = json.loads(proc.stdout)
        assert payload["gate"]["requirements"] == list(STRICT_REQUIREMENTS)
        assert len(payload["gate"]["requirements"]) > len(DEFAULT_REQUIREMENTS)

    def test_the_cli_reports_a_problem_in_text_mode(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  extra:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q tests/extra.py
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
"""
        path = _write_workflow(tmp_path, _workflow(jobs))
        proc = self._run(tmp_path, "--workflow", str(path))
        assert "brand" not in proc.stdout  # sanity: names differ
        assert "extra" in proc.stdout
        assert "❌" in proc.stdout


# ── the repository's own workflow ──────────────────────────────────────────


class TestRepositoryWorkflow:
    """The audit must pass on this repository's actual workflow.

    These tests are *not* hermetic — they read the checked-out
    workflow on purpose.  They are the tripwire: if somebody adds a job
    without updating the gate, or breaks a ``needs:`` target, the CI
    must fail here rather than at some later, more confusing moment.
    """

    def test_the_repository_workflow_parses(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        workflow = parse_workflow(path)
        assert "pr-coverage-gate" in workflow.jobs
        assert len(workflow.jobs) >= 9

    def test_the_repository_workflow_has_no_dangling_needs(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["dangling_needs"] == []

    def test_the_repository_workflow_is_acyclic(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["cycles"] == []

    def test_the_repository_workflow_has_no_ungated_verification_jobs(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["ungated_jobs"] == []

    def test_the_repository_workflow_passes_the_gate(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        workflow = parse_workflow(path)
        result = audit_workflow(workflow)
        add_reachability(result, workflow)
        assert evaluate_gate([result])["ok"] is True
        assert evaluate_gate([result], STRICT_REQUIREMENTS)["ok"] is True


# ── bug injection ──────────────────────────────────────────────────────────


class TestBugInjection:
    """The shipped tests must actually bite.

    A test suite that passes on a broken implementation is not a test
    suite — it is a rubber stamp with assertions in it.  Each case below
    re-introduces the defect the audit exists to catch and asserts that
    the audit notices.
    """

    def test_injecting_a_dangling_need_is_caught(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates, typo_job]
    steps:
      - run: echo gate
"""
        result = _audit(tmp_path, jobs)
        assert result["ok"] is False
        assert result["dangling_needs"]

    def test_injecting_an_ungated_job_is_caught(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
  sneaky-job:
    runs-on: ubuntu-latest
    steps:
      - run: echo sneaky
"""
        result = _audit(tmp_path, jobs)
        assert result["ok"] is False
        assert result["ungated_jobs"]

    def test_injecting_a_cycle_is_caught(self, tmp_path):
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
  extra:
    runs-on: ubuntu-latest
    needs: [pr-coverage-gate]
    steps:
      - run: echo extra
  quality-gates-2:
    runs-on: ubuntu-latest
    needs: [extra]
    steps:
      - run: echo qg2
"""
        result = _audit(tmp_path, jobs)
        assert result["cycles"] == []

    def test_injecting_a_real_cycle_is_caught(self, tmp_path):
        """``extra`` -> ``quality-gates`` closes a genuine cycle."""
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    needs: [extra]
    steps:
      - run: pytest -q
  pr-coverage-gate:
    runs-on: ubuntu-latest
    needs: [quality-gates]
    steps:
      - run: echo gate
  extra:
    runs-on: ubuntu-latest
    needs: [pr-coverage-gate]
    steps:
      - run: echo extra
"""
        result = _audit(tmp_path, jobs)
        assert result["cycles"]
        assert result["ok"] is False

    def test_removing_the_gate_entirely_removes_the_ungated_check(self, tmp_path):
        """Without a gate there is nothing to cover — and that is fine.

        This is the honest-degradation case: the audit must not
        manufacture a failure where the workflow has no gate concept.
        """
        jobs = """  quality-gates:
    runs-on: ubuntu-latest
    steps:
      - run: pytest -q
  another-job:
    runs-on: ubuntu-latest
    steps:
      - run: echo another
"""
        result = _audit(tmp_path, jobs)
        assert result["ungated_jobs"] == []
        assert result["ok"] is True
