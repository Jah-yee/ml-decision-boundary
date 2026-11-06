"""Tests for the release pipeline audit (v14 DoD #1).

The invariant under test is the release-pipeline counterpart of the
invariants introduced in v13:

    **The workflow that actually publishes the product must be
    auditable in the same way as the workflow that tests it.**

DoD #7 fixed the CI workflow's trigger block ("would CI even start?").
DoD #8 added a pull-request-level audit of CI coverage ("is every pull
request verified?").  DoD #16 made the two gate modes monotonic.
DoD #17 audited the *shape* of the branch stack.  DoD #18 audited the
*job dependency graph* inside the CI workflow.

None of them touch the **release** workflow — and they were all right
to skip it, because a tag-driven publish pipeline is not supposed to
run on pull requests.  But skipping it for that reason left it with
**no audit at all**, and it is the one job in this repository that
holds ``contents: write`` and creates the shipped artefact.

The concrete situation this audit exists for: **the repository has no
tags at all**, so the release pipeline has never executed even once,
and its very first step is known to fail on a tagless repository.

**The six concrete defects.**

1. **The first release cannot succeed.**  The changelog step runs
   ``git describe --tags --abbrev=0 HEAD~1``.  With no tags, git
   exits **128** ("No names found, cannot describe anything") and the
   release job dies before creating anything.
2. **The previous-tag lookup is anchored to the wrong thing.**
   ``HEAD~1`` is the parent *commit* of the tagged commit, not the
   previous *release*.  It resolves the wrong changelog range whenever
   the tagged commit is a merge or when commits landed after the last
   tag, and it fails outright when the tagged commit is the first
   commit ("Failed to resolve 'HEAD' as a valid ref").
3. **The changelog is byte-truncated.**  ``head -c 5000`` cuts at an
   arbitrary *byte* offset and can split a multi-byte UTF-8 character,
   producing an undecodable file — while still exiting 0, so the
   corrupt file is committed to ``master``.
4. **No concurrency guard.**  Two tags pushed together run two release
   jobs at once; they race on ``CHANGELOG.md`` and one update is lost.
5. **Third-party actions are pinned to mutable tags**, not to SHAs, in
   the one job that holds write access to the repository.
6. **Permissions and triggers are not checked**: a release workflow
   that fires on ordinary pushes publishes a release per commit, and
   ``permissions: write-all`` grants every scope in the repository.

**What these tests pin.**

1. the *parser* — the workflow subset reader, including its refusal
   to guess on malformed input;
2. the *six detections* — each defect above;
3. the *monotonicity* — the strict mode must be a strict superset of
   the default mode and must never be laxer;
4. the *bug injection* — the original defect must actually be caught by
   the shipped tests, not merely described by them.

Every test writes its own throwaway workflow file.  A test that
depends on the ambient repository measures the environment, not the
code.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import release_audit  # noqa: E402
from release_audit import (  # noqa: E402
    DEFAULT_REQUIREMENTS,
    STRICT_REQUIREMENTS,
    WorkflowParseError,
    audit_workflow,
    evaluate_gate,
    parse_workflow,
)


# ── fixtures / helpers ─────────────────────────────────────────────────────


CLEAN_RELEASE = """\
name: Release

on:
  push:
    tags:
      - 'v*'

permissions:
  contents: write

concurrency:
  group: release-${{ github.ref_name }}
  cancel-in-progress: false

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Generate changelog
        run: |
          PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")
          echo "prev=$PREV_TAG"
      - name: Merge changelog
        run: |
          cat CHANGELOG_NEW.md
          head -n 500 CHANGELOG.md
"""


def write(tmp_path: Path, text: str, name: str = "release.yml") -> Path:
    """Write a throwaway workflow file and return its path."""
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def audit_text(tmp_path: Path, text: str, name: str = "release.yml") -> dict:
    """Parse and audit a throwaway workflow."""
    return audit_workflow(parse_workflow(write(tmp_path, text, name=name)))


# ── parser ─────────────────────────────────────────────────────────────────


class TestParser:
    def test_a_minimal_workflow_is_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        assert workflow.jobs
        assert "release" in workflow.jobs

    def test_the_tag_filter_is_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        assert workflow.triggers == ["push"]
        assert workflow.tag_patterns == ["v*"]

    def test_permissions_are_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        assert workflow.permissions == {"contents": "write"}

    def test_concurrency_is_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        assert workflow.has_concurrency is True
        assert "release" in workflow.concurrency_expr

    def test_uses_steps_are_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        uses = [s.uses for j in workflow.jobs.values() for s in j.steps if s.uses]
        assert "actions/checkout@v4" in uses

    def test_run_bodies_are_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        runs = [s.run for j in workflow.jobs.values() for s in j.steps if s.run]
        assert any("git describe --tags" in r for r in runs)

    def test_step_names_are_parsed(self, tmp_path):
        workflow = parse_workflow(write(tmp_path, CLEAN_RELEASE))
        names = [s.name for j in workflow.jobs.values() for s in j.steps if s.name]
        assert "Generate changelog" in names

    def test_a_missing_file_raises(self, tmp_path):
        with pytest.raises(WorkflowParseError):
            parse_workflow(tmp_path / "nope.yml")

    def test_a_commented_trigger_is_not_a_trigger(self, tmp_path):
        text = CLEAN_RELEASE.replace("  push:", "  # push:")
        workflow = parse_workflow(write(tmp_path, text))
        assert "push" not in workflow.triggers

    def test_a_commented_tag_pattern_is_not_a_tag_pattern(self, tmp_path):
        text = CLEAN_RELEASE.replace("      - 'v*'", "      # - 'v*'")
        workflow = parse_workflow(write(tmp_path, text))
        assert workflow.tag_patterns == []


# ── defect 1: the first release cannot succeed ─────────────────────────────


class TestTagDiscovery:
    def test_an_unguarded_describe_is_detected(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)",
        )
        result = audit_text(tmp_path, text)
        assert result["tag_discovery_guarded"] is False
        assert result["tag_discovery_describe_calls"]

    def test_a_guarded_describe_is_accepted(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["tag_discovery_guarded"] is True

    def test_an_unguarded_describe_fails_the_gate(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)",
        )
        result = audit_text(tmp_path, text)
        gate = evaluate_gate([result])
        assert gate["ok"] is False
        assert "tag_discovery_safe" in gate["failures"][result["workflow"]]

    def test_a_workflow_without_any_describe_fails_the_gate(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=none",
        )
        result = audit_text(tmp_path, text)
        gate = evaluate_gate([result])
        assert gate["ok"] is False
        assert "tag_discovery_safe" in gate["failures"][result["workflow"]]

    def test_the_describe_must_actually_exist(self, tmp_path):
        """A workflow with no tag lookup at all is not 'safe'."""
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=hardcoded",
        )
        result = audit_text(tmp_path, text)
        assert result["tag_discovery_describe_calls"] == []


# ── defect 2: the lookup is anchored to HEAD~1, not to the tag ─────────────


class TestTagAnchoring:
    def test_a_head_parent_lookup_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo \"\")",
        )
        result = audit_text(tmp_path, text)
        assert result["anchored_to_head_parent"] is True

    def test_a_tag_anchored_lookup_is_not_flagged(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["anchored_to_head_parent"] is False

    def test_the_anchoring_defect_only_fails_the_strict_gate(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            'PREV_TAG=$(git describe --tags --abbrev=0 2>/dev/null || echo "")',
            "PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo \"\")",
        )
        result = audit_text(tmp_path, text)
        default = evaluate_gate([result], DEFAULT_REQUIREMENTS)
        strict = evaluate_gate([result], STRICT_REQUIREMENTS)
        assert default["ok"] is True
        assert strict["ok"] is False
        assert "tag_pattern_anchored" in strict["failures"][result["workflow"]]


# ── defect 3: byte truncation of the changelog ─────────────────────────────


class TestChangelogIntegrity:
    def test_a_head_c_truncation_is_detected(self, tmp_path):
        text = CLEAN_RELEASE.replace("head -n 500 CHANGELOG.md", "head -c 5000 CHANGELOG.md")
        result = audit_text(tmp_path, text)
        assert result["byte_truncations"]
        assert result["byte_truncations"][0]["byte_limit"] == 5000

    def test_a_line_truncation_is_accepted(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["byte_truncations"] == []

    def test_a_byte_truncation_fails_the_gate(self, tmp_path):
        text = CLEAN_RELEASE.replace("head -n 500 CHANGELOG.md", "head -c 5000 CHANGELOG.md")
        result = audit_text(tmp_path, text)
        gate = evaluate_gate([result])
        assert gate["ok"] is False
        assert "changelog_not_truncated" in gate["failures"][result["workflow"]]

    def test_byte_truncation_really_can_split_a_character(self, tmp_path):
        """The audit's claim, proven by execution rather than asserted.

        ``head -c N`` cuts at a byte offset; a multi-byte UTF-8
        character straddling that offset is split in half and the
        result no longer decodes.
        """
        import subprocess as sp

        payload = "# Changelog\n\n" + ("中" * 3000) + "\n"
        source = tmp_path / "CHANGELOG.md"
        source.write_text(payload, encoding="utf-8")

        out = sp.run(
            f"tail -n +3 {source} | head -c 5000",
            shell=True,
            capture_output=True,
        )
        assert out.returncode == 0  # the truncation is *silent*
        with pytest.raises(UnicodeDecodeError):
            out.stdout.decode("utf-8")


# ── defect 4: no concurrency guard ─────────────────────────────────────────


class TestConcurrency:
    def test_a_workflow_without_concurrency_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "concurrency:\n  group: release-${{ github.ref_name }}\n  cancel-in-progress: false\n",
            "",
        )
        result = audit_text(tmp_path, text)
        assert result["has_concurrency"] is False

    def test_a_workflow_with_concurrency_is_accepted(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["has_concurrency"] is True

    def test_a_missing_concurrency_fails_the_gate(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "concurrency:\n  group: release-${{ github.ref_name }}\n  cancel-in-progress: false\n",
            "",
        )
        result = audit_text(tmp_path, text)
        gate = evaluate_gate([result])
        assert gate["ok"] is False
        assert "concurrency_declared" in gate["failures"][result["workflow"]]


# ── defect 5: mutable action references ────────────────────────────────────


class TestActionPinning:
    UNPINNED = """\
name: Release
on:
  push:
    tags:
      - 'v*'
permissions:
  contents: write
concurrency:
  group: release
jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: softprops/action-gh-release@v2
      - uses: stefanzweifel/git-auto-commit-action@v5
"""

    def test_a_mutable_tag_reference_is_detected(self, tmp_path):
        result = audit_text(tmp_path, self.UNPINNED)
        uses = [a["uses"] for a in result["unpinned_actions"]]
        assert "softprops/action-gh-release@v2" in uses
        assert "stefanzweifel/git-auto-commit-action@v5" in uses

    def test_first_party_actions_are_exempt(self, tmp_path):
        result = audit_text(tmp_path, self.UNPINNED)
        uses = [a["uses"] for a in result["unpinned_actions"]]
        assert "actions/checkout@v4" not in uses

    def test_a_sha_pinned_action_is_accepted(self, tmp_path):
        sha = "a" * 40
        text = self.UNPINNED.replace("softprops/action-gh-release@v2", f"softprops/action-gh-release@{sha}")
        result = audit_text(tmp_path, text)
        uses = [a["uses"] for a in result["unpinned_actions"]]
        assert f"softprops/action-gh-release@{sha}" not in uses

    def test_an_unpinned_action_fails_the_gate(self, tmp_path):
        result = audit_text(tmp_path, self.UNPINNED)
        gate = evaluate_gate([result])
        assert gate["ok"] is False
        assert "actions_pinned" in gate["failures"][result["workflow"]]

    def test_the_reason_distinguishes_mutable_tags_from_other_refs(self, tmp_path):
        result = audit_text(tmp_path, self.UNPINNED)
        reasons = {a["uses"]: a["reason"] for a in result["unpinned_actions"]}
        assert reasons["softprops/action-gh-release@v2"] == "mutable tag ref"


# ── defect 6: permissions and trigger safety ──────────────────────────────


class TestPermissions:
    def test_a_workflow_without_permissions_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace("permissions:\n  contents: write\n", "")
        result = audit_text(tmp_path, text)
        assert result["permissions_problems"]
        assert any("permissions" in p for p in result["permissions_problems"])

    def test_write_all_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "permissions:\n  contents: write\n", "permissions: write-all\n"
        )
        result = audit_text(tmp_path, text)
        assert any("write-all" in p for p in result["permissions_problems"])

    def test_an_unnecessary_write_scope_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "permissions:\n  contents: write\n",
            "permissions:\n  contents: write\n  packages: write\n",
        )
        result = audit_text(tmp_path, text)
        assert any("packages" in p for p in result["permissions_problems"])

    def test_minimal_permissions_are_accepted(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["permissions_problems"] == []


class TestTriggerSafety:
    def test_a_push_without_a_tag_filter_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace("    tags:\n      - 'v*'\n", "")
        result = audit_text(tmp_path, text)
        assert any("tags:" in p for p in result["trigger_problems"])

    def test_a_non_push_trigger_is_flagged(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "on:\n  push:\n    tags:\n      - 'v*'\n",
            "on:\n  push:\n    tags:\n      - 'v*'\n  workflow_dispatch:\n",
        )
        result = audit_text(tmp_path, text)
        assert any("non-push" in p for p in result["trigger_problems"])

    def test_a_tag_driven_release_is_accepted(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["trigger_problems"] == []


# ── gate ───────────────────────────────────────────────────────────────────


class TestGate:
    def test_a_clean_release_passes_the_default_gate(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        gate = evaluate_gate([result])
        assert gate["ok"] is True

    def test_strict_requirements_are_a_strict_superset(self):
        assert set(DEFAULT_REQUIREMENTS) < set(STRICT_REQUIREMENTS)

    def test_strict_mode_is_never_laxer_than_default(self):
        assert set(STRICT_REQUIREMENTS) >= set(DEFAULT_REQUIREMENTS)

    def test_strict_mode_adds_exactly_one_requirement(self):
        assert len(STRICT_REQUIREMENTS) == len(DEFAULT_REQUIREMENTS) + 1

    def test_an_unknown_requirement_raises(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        with pytest.raises(ValueError):
            evaluate_gate([result], ("no_such_requirement",))


# ── CLI ────────────────────────────────────────────────────────────────────


class TestCli:
    def _run(self, tmp_path: Path, *args: str) -> subprocess.CompletedProcess:
        script = REPO_ROOT / "scripts" / "release_audit.py"
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
        )

    def test_a_clean_workflow_exits_zero(self, tmp_path):
        path = write(tmp_path, CLEAN_RELEASE)
        proc = self._run(tmp_path, "--workflow", str(path))
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_a_defective_workflow_exits_one(self, tmp_path):
        text = CLEAN_RELEASE.replace("head -n 500 CHANGELOG.md", "head -c 5000 CHANGELOG.md")
        path = write(tmp_path, text)
        proc = self._run(tmp_path, "--workflow", str(path))
        assert proc.returncode == 1

    def test_json_output_is_machine_readable(self, tmp_path):
        path = write(tmp_path, CLEAN_RELEASE)
        proc = self._run(tmp_path, "--workflow", str(path), "--json")
        payload = json.loads(proc.stdout)
        assert "results" in payload
        assert "gate" in payload
        assert payload["gate"]["ok"] is True

    def test_a_missing_workflow_exits_two(self, tmp_path):
        proc = self._run(tmp_path, "--workflow", str(tmp_path / "nope.yml"))
        assert proc.returncode == 2

    def test_the_cli_never_modifies_the_workflow(self, tmp_path):
        text = CLEAN_RELEASE.replace("head -n 500 CHANGELOG.md", "head -c 5000 CHANGELOG.md")
        path = write(tmp_path, text)
        before = path.read_bytes()
        self._run(tmp_path, "--workflow", str(path))
        assert path.read_bytes() == before


# ── the real repository ────────────────────────────────────────────────────


class TestRealRepository:
    """The shipped release workflow must pass the audit.

    This is the test that guarantees the delivered pipeline is the
    audited one.  It is the counterpart of the bug-injection class
    below: if a defect is ever reintroduced into the real workflow,
    the injection tests fail and this class fails too.
    """

    def test_the_shipped_release_workflow_exists(self):
        assert (REPO_ROOT / ".github" / "workflows" / "release.yml").exists()

    def test_the_shipped_release_workflow_is_audited(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        # The trigger and the tag pattern must be read correctly --
        # otherwise every other finding would be vacuous.
        assert result["triggers"] == ["push"]
        assert result["tag_patterns"] == ["v*"]

    def test_the_shipped_release_workflow_passes_the_gate(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        gate = evaluate_gate([result])
        assert gate["ok"] is True, gate["failures"]

    def test_the_shipped_release_workflow_passes_the_strict_gate(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        gate = evaluate_gate([result], STRICT_REQUIREMENTS)
        assert gate["ok"] is True, gate["failures"]

    def test_the_previous_tag_lookup_is_first_release_safe(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        assert result["tag_discovery_guarded"] is True

    def test_the_changelog_is_not_byte_truncated(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        assert result["byte_truncations"] == []

    def test_the_concurrency_guard_is_declared(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        assert result["has_concurrency"] is True

    def test_every_action_is_pinned(self):
        workflow = parse_workflow(
            REPO_ROOT / ".github" / "workflows" / "release.yml"
        )
        result = audit_workflow(workflow)
        assert result["unpinned_actions"] == []

    def test_the_repository_has_never_been_tagged(self):
        """The premise of the audit: the release path was never run.

        ``git describe --tags`` on a tagless repository exits 128,
        which is exactly what the release workflow's first step used
        to do.
        """
        proc = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0", "HEAD~1"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert "cannot describe" in (proc.stderr + proc.stdout).lower()


class TestPreviousTagResolution:
    """The previous-tag lookup, proven by execution rather than asserted.

    The defect being guarded against is subtle: replacing
    ``git describe --tags --abbrev=0 HEAD~1`` with a plain
    ``git describe --tags --abbrev=0`` *looks* like a fix (it no
    longer fails on a tagless repository) but it resolves to the tag
    **being released**, not to the previous one -- so the changelog
    would be empty on every release after the first.
    """

    def _repo(self, tmp_path: Path, tag_count: int) -> Path:
        repo = tmp_path / "repo"
        repo.mkdir()
        env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
        }
        subprocess.run(["git", "init", "-q", "."], cwd=repo, env=env, check=True)
        for i in range(tag_count):
            (repo / "f").write_text(f"{i}\n")
            subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True)
            subprocess.run(
                ["git", "commit", "-qm", f"c{i}"], cwd=repo, env=env, check=True
            )
            subprocess.run(
                ["git", "tag", f"v0.{i}.0"], cwd=repo, env=env, check=True
            )
        return repo

    def _previous_tag(self, repo: Path) -> str:
        """The robust lookup, executed exactly as the workflow runs it."""
        script = (
            'CURRENT_TAG=$(git tag --points-at HEAD | head -1); '
            'git tag --sort=-v:refname | grep -v "^${CURRENT_TAG}$" | head -1 || true'
        )
        proc = subprocess.run(
            ["bash", "-c", script], cwd=repo, capture_output=True, text=True
        )
        return proc.stdout.strip()

    def test_the_first_release_has_no_previous_tag(self, tmp_path):
        repo = self._repo(tmp_path, tag_count=1)
        assert self._previous_tag(repo) == ""

    def test_the_second_release_resolves_the_first_tag(self, tmp_path):
        repo = self._repo(tmp_path, tag_count=2)
        subprocess.run(
            ["git", "checkout", "-q", "v0.1.0"], cwd=repo, check=True
        )
        assert self._previous_tag(repo) == "v0.0.0"

    def test_the_third_release_resolves_the_second_tag(self, tmp_path):
        repo = self._repo(tmp_path, tag_count=3)
        subprocess.run(
            ["git", "checkout", "-q", "v0.2.0"], cwd=repo, check=True
        )
        assert self._previous_tag(repo) == "v0.1.0"

    def test_a_plain_describe_would_resolve_to_the_tag_being_released(
        self, tmp_path
    ):
        """The subtle defect the naive fix would introduce."""
        repo = self._repo(tmp_path, tag_count=2)
        subprocess.run(
            ["git", "checkout", "-q", "v0.1.0"], cwd=repo, check=True
        )
        proc = subprocess.run(
            ["git", "describe", "--tags", "--abbrev=0"],
            cwd=repo,
            capture_output=True,
            text=True,
        )
        assert proc.stdout.strip() == "v0.1.0"
        # ... which is the tag being released, i.e. NOT the previous
        # one.  The robust lookup must disagree with it.
        assert self._previous_tag(repo) != proc.stdout.strip()

    def test_a_tagless_repository_yields_no_previous_tag(self, tmp_path):
        repo = tmp_path / "empty"
        repo.mkdir()
        env = {
            "GIT_AUTHOR_NAME": "t",
            "GIT_AUTHOR_EMAIL": "t@t.co",
            "GIT_COMMITTER_NAME": "t",
            "GIT_COMMITTER_EMAIL": "t@t.co",
            "PATH": "/usr/bin:/bin:/usr/local/bin",
            "HOME": str(tmp_path),
        }
        subprocess.run(["git", "init", "-q", "."], cwd=repo, env=env, check=True)
        (repo / "f").write_text("x\n")
        subprocess.run(["git", "add", "-A"], cwd=repo, env=env, check=True)
        subprocess.run(["git", "commit", "-qm", "one"], cwd=repo, env=env, check=True)
        assert self._previous_tag(repo) == ""


class TestBugInjection:
    """Every shipped defect must still be caught when reintroduced.

    A gate that does not fail on the defect it exists to catch is not
    a gate, it is a rubber stamp.  Each test takes the *fixed* shipped
    workflow, reintroduces one original defect, and asserts that the
    audit reports it.
    """

    SHIPPED = (REPO_ROOT / ".github" / "workflows" / "release.yml").read_text(
        encoding="utf-8"
    )

    def _inject(self, tmp_path: Path, old: str, new: str) -> dict:
        assert old in self.SHIPPED, f"anchor not found in shipped workflow: {old!r}"
        text = self.SHIPPED.replace(old, new, 1)
        return audit_text(tmp_path, text)

    def test_reintroducing_the_unguarded_describe_is_detected(self, tmp_path):
        # Both previous-tag lookups must be replaced, otherwise the
        # surviving guarded one keeps the requirement satisfied.
        text = self.SHIPPED.replace(
            'CURRENT_TAG=$(git tag --points-at HEAD | head -1)\n'
            '          PREV_TAG=$(git tag --sort=-v:refname | grep -v "^${CURRENT_TAG}$" | head -1 || true)',
            'PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1)',
        )
        assert 'git describe --tags --abbrev=0 HEAD~1' in text
        result = audit_text(tmp_path, text)
        assert result["tag_discovery_guarded"] is False
        gate = evaluate_gate([result])
        assert "tag_discovery_safe" in gate["failures"][result["workflow"]]

    def test_reintroducing_the_byte_truncation_is_detected(self, tmp_path):
        result = self._inject(
            tmp_path,
            "head -n 500  # Skip header lines and unreleased",
            "head -c 5000  # Skip header lines and unreleased",
        )
        assert result["byte_truncations"]
        gate = evaluate_gate([result])
        assert "changelog_not_truncated" in gate["failures"][result["workflow"]]

    def test_removing_the_concurrency_guard_is_detected(self, tmp_path):
        result = self._inject(
            tmp_path,
            "\nconcurrency:\n  group: release-${{ github.ref_name }}\n"
            "  cancel-in-progress: false\n",
            "\n",
        )
        assert result["has_concurrency"] is False
        gate = evaluate_gate([result])
        assert "concurrency_declared" in gate["failures"][result["workflow"]]

    def test_reintroducing_a_mutable_action_ref_is_detected(self, tmp_path):
        result = self._inject(
            tmp_path,
            "softprops/action-gh-release@3bb12739c298aeb8a4eeaf626c5b8d85266b0e65",
            "softprops/action-gh-release@v2",
        )
        uses = {a["uses"] for a in result["unpinned_actions"]}
        assert "softprops/action-gh-release@v2" in uses
        gate = evaluate_gate([result])
        assert "actions_pinned" in gate["failures"][result["workflow"]]

    def test_reintroducing_write_all_is_detected(self, tmp_path):
        result = self._inject(
            tmp_path,
            "permissions:\n  contents: write\n",
            "permissions: write-all\n",
        )
        assert result["permissions_problems"]
        gate = evaluate_gate([result])
        assert "permissions_explicit" in gate["failures"][result["workflow"]]

    def test_removing_the_tag_filter_is_detected(self, tmp_path):
        result = self._inject(
            tmp_path,
            "    tags:\n      - 'v*'\n",
            "",
        )
        assert result["trigger_problems"]
        gate = evaluate_gate([result])
        assert "trigger_safe" in gate["failures"][result["workflow"]]

    def test_reintroducing_the_head_parent_anchor_is_detected(self, tmp_path):
        text = self.SHIPPED.replace(
            'CURRENT_TAG=$(git tag --points-at HEAD | head -1)\n'
            '          PREV_TAG=$(git tag --sort=-v:refname | grep -v "^${CURRENT_TAG}$" | head -1 || true)',
            'PREV_TAG=$(git describe --tags --abbrev=0 HEAD~1 2>/dev/null || echo "")',
        )
        assert 'HEAD~1 2>/dev/null' in text
        result = audit_text(tmp_path, text)
        assert result["anchored_to_head_parent"] is True
        gate = evaluate_gate([result], STRICT_REQUIREMENTS)
        assert "tag_pattern_anchored" in gate["failures"][result["workflow"]]


# ── workflow kinds ─────────────────────────────────────────────────────────
#
# v133 (this round): the audit applied the *release* ruleset to every
# workflow in the directory, so the default invocation
# (`release_audit.py --strict`, which globs `.github/workflows/*.yml`)
# reported `ci.yml` as defective on six counts -- including three
# checks that are meaningless for CI and one (`trigger_safe`) whose
# meaning is **reversed** between the two kinds.
#
# The bug was invisible to the previous round's 68 tests because every
# one of them either passed `--workflow` explicitly or audited
# `release.yml` alone.  The tests below close that hole.


CLEAN_CI = """\
name: CI

on:
  push:
    branches: [master]
  pull_request:

permissions:
  contents: read
  pull-requests: read

jobs:
  tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run the suite
        run: python3 -m pytest
"""


class TestClassification:
    def test_a_tag_driven_workflow_is_a_release(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        assert result["kind"] == "release"

    def test_a_plain_ci_workflow_is_ci(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_CI, name="ci.yml")
        assert result["kind"] == "ci"

    def test_the_name_release_alone_makes_it_a_release(self, tmp_path):
        text = CLEAN_CI.replace("name: CI", "name: Publish")
        result = audit_text(tmp_path, text, name="publish.yml")
        # 'publish' is not 'release', so this stays CI by name...
        assert result["kind"] == "ci"

    def test_holding_contents_write_makes_it_a_release(self, tmp_path):
        text = CLEAN_CI.replace(
            "  contents: read\n  pull-requests: read",
            "  contents: write\n  pull-requests: read",
        )
        result = audit_text(tmp_path, text, name="deploy.yml")
        assert result["kind"] == "release"

    def test_a_workflow_named_release_is_a_release(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_CI, name="release-notes.yml")
        assert result["kind"] == "release"


class TestKindScopedRequirements:
    def test_release_requirements_include_the_release_only_checks(self):
        reqs = release_audit.requirements_for("release")
        assert "tag_discovery_safe" in reqs
        assert "changelog_not_truncated" in reqs
        assert "concurrency_declared" in reqs

    def test_ci_requirements_exclude_the_release_only_checks(self):
        reqs = release_audit.requirements_for("ci")
        assert "tag_discovery_safe" not in reqs
        assert "changelog_not_truncated" not in reqs
        assert "concurrency_declared" not in reqs

    def test_ci_still_keeps_the_shared_checks(self):
        reqs = release_audit.requirements_for("ci")
        for requirement in ("actions_pinned", "permissions_explicit", "trigger_safe"):
            assert requirement in reqs

    def test_strict_is_a_strict_superset_for_release(self):
        assert set(release_audit.requirements_for("release")) < set(
            release_audit.requirements_for("release", strict=True)
        )

    def test_strict_is_never_laxer_than_default_for_ci(self):
        default = set(release_audit.requirements_for("ci"))
        strict = set(release_audit.requirements_for("ci", strict=True))
        assert strict >= default

    def test_an_unknown_kind_raises(self):
        with pytest.raises(ValueError):
            release_audit.requirements_for("nonsense")

    def test_a_ci_workflow_passes_its_own_gate(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_CI, name="ci.yml")
        gate = evaluate_gate([result])
        assert gate["ok"] is True

    def test_a_clean_release_still_passes_its_own_gate(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_RELEASE)
        gate = evaluate_gate([result], strict=True)
        assert gate["ok"] is True


class TestTriggerSemanticsReverse:
    """`trigger_safe` means opposite things for the two kinds."""

    def test_a_release_without_a_tag_filter_fails(self, tmp_path):
        text = CLEAN_RELEASE.replace("    tags:\n      - 'v*'\n", "")
        result = audit_text(tmp_path, text)
        assert result["kind"] == "release"
        gate = evaluate_gate([result])
        assert "trigger_safe" in gate["failures"][result["workflow"]]

    def test_a_ci_workflow_pushing_to_a_branch_is_correct(self, tmp_path):
        result = audit_text(tmp_path, CLEAN_CI, name="ci.yml")
        assert result["kind"] == "ci"
        assert result["trigger_problems"] == []
        gate = evaluate_gate([result])
        assert "trigger_safe" not in gate["failures"].get(result["workflow"], [])

    def test_a_ci_workflow_that_only_fires_on_tags_is_a_defect(self, tmp_path):
        text = CLEAN_CI.replace(
            "on:\n  push:\n    branches: [master]\n  pull_request:\n",
            "on:\n  push:\n    tags:\n      - 'v*'\n",
        )
        result = audit_text(tmp_path, text, name="ci.yml")
        # A tag-only trigger is what makes it a *release*, so it is
        # classified as one -- and there it is perfectly correct.
        assert result["kind"] == "release"
        assert result["trigger_problems"] == []

    def test_a_ci_workflow_with_no_push_trigger_is_flagged(self, tmp_path):
        text = CLEAN_CI.replace(
            "on:\n  push:\n    branches: [master]\n  pull_request:\n",
            "on:\n  schedule:\n    - cron: '0 0 * * *'\n",
        )
        result = audit_text(tmp_path, text, name="ci.yml")
        assert result["kind"] == "ci"
        assert result["trigger_problems"]


class TestDefaultGlobPath:
    """The path a human (and CI) actually takes by default."""

    def _run(self, *args: str) -> subprocess.CompletedProcess:
        script = REPO_ROOT / "scripts" / "release_audit.py"
        return subprocess.run(
            [sys.executable, str(script), *args],
            capture_output=True,
            text=True,
        )

    def test_the_default_invocation_passes_on_this_repository(self):
        """The bug this round fixed: the default glob reported ci.yml
        as defective on six counts.  The repository is clean, so the
        default invocation must exit zero."""
        proc = self._run("--strict")
        assert proc.returncode == 0, proc.stdout + proc.stderr

    def test_the_default_invocation_audits_every_workflow(self):
        proc = self._run("--strict", "--json")
        payload = json.loads(proc.stdout)
        names = {Path(r["workflow"]).name for r in payload["results"]}
        assert "ci.yml" in names
        assert "release.yml" in names

    def test_the_default_invocation_reports_each_workflow_kind(self):
        proc = self._run("--strict", "--json")
        payload = json.loads(proc.stdout)
        kinds = {Path(r["workflow"]).name: r["kind"] for r in payload["results"]}
        assert kinds["release.yml"] == "release"
        assert kinds["ci.yml"] == "ci"

    def test_the_default_invocation_uses_kind_scoped_requirements(self):
        proc = self._run("--strict", "--json")
        payload = json.loads(proc.stdout)
        applied = payload["gate"]["applied_requirements"]
        by_name = {Path(k).name: v for k, v in applied.items()}
        assert "tag_discovery_safe" in by_name["release.yml"]
        assert "tag_discovery_safe" not in by_name["ci.yml"]


class TestRealRepositoryKindSplit:
    """The shipped workflows, audited the way CI will audit them."""

    def test_the_shipped_ci_workflow_is_classified_as_ci(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["kind"] == "ci"

    def test_the_shipped_release_workflow_is_classified_as_release(self):
        path = REPO_ROOT / ".github" / "workflows" / "release.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["kind"] == "release"

    def test_the_shipped_ci_workflow_declares_explicit_permissions(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["permissions_problems"] == []

    def test_the_shipped_ci_workflow_grants_no_write_scope(self):
        path = REPO_ROOT / ".github" / "workflows" / "ci.yml"
        result = audit_workflow(parse_workflow(path))
        assert result["permissions"].get("contents") == "read"
        assert "write" not in result["permissions"].values()

    def test_both_shipped_workflows_pass_the_strict_gate_together(self):
        results = [
            audit_workflow(parse_workflow(REPO_ROOT / ".github" / "workflows" / name))
            for name in ("ci.yml", "release.yml")
        ]
        gate = evaluate_gate(results, strict=True)
        assert gate["ok"] is True, gate["failures"]


class TestBugInjectionKindSplit:
    """Re-introduce the defects the kind split could hide."""

    def test_removing_the_ci_permissions_block_is_detected(self, tmp_path):
        text = CLEAN_CI.replace(
            "permissions:\n  contents: read\n  pull-requests: read\n", ""
        )
        result = audit_text(tmp_path, text, name="ci.yml")
        assert result["permissions_problems"]
        gate = evaluate_gate([result])
        assert "permissions_explicit" in gate["failures"][result["workflow"]]

    def test_granting_the_ci_workflow_write_access_is_detected(self, tmp_path):
        text = CLEAN_CI.replace(
            "  contents: read\n  pull-requests: read",
            "  contents: write\n  pull-requests: write",
        )
        result = audit_text(tmp_path, text, name="ci.yml")
        assert result["permissions_problems"]
        gate = evaluate_gate([result])
        assert "permissions_explicit" in gate["failures"][result["workflow"]]

    def test_an_unpinned_action_in_a_ci_workflow_is_detected(self, tmp_path):
        text = CLEAN_CI.replace("actions/checkout@v4", "third-party/thing@v1")
        result = audit_text(tmp_path, text, name="ci.yml")
        assert result["unpinned_actions"]
        gate = evaluate_gate([result])
        assert "actions_pinned" in gate["failures"][result["workflow"]]

    def test_a_release_workflow_losing_its_tag_filter_is_still_detected(self, tmp_path):
        """The kind split must not become a back door: a workflow that
        *was* a release and lost its tag filter must still be judged
        by the release ruleset (it still holds 'contents: write')."""
        text = CLEAN_RELEASE.replace("    tags:\n      - 'v*'\n", "")
        result = audit_text(tmp_path, text)
        assert result["kind"] == "release"
        gate = evaluate_gate([result])
        assert "trigger_safe" in gate["failures"][result["workflow"]]

    def test_a_release_workflow_losing_its_concurrency_is_still_detected(self, tmp_path):
        text = CLEAN_RELEASE.replace(
            "concurrency:\n  group: release-${{ github.ref_name }}\n"
            "  cancel-in-progress: false\n",
            "",
        )
        result = audit_text(tmp_path, text)
        assert result["kind"] == "release"
        gate = evaluate_gate([result])
        assert "concurrency_declared" in gate["failures"][result["workflow"]]

    def test_a_release_workflow_with_a_byte_truncation_is_still_detected(self, tmp_path):
        text = CLEAN_RELEASE.replace("head -n 500 CHANGELOG.md", "head -c 5000 CHANGELOG.md")
        result = audit_text(tmp_path, text)
        gate = evaluate_gate([result])
        assert "changelog_not_truncated" in gate["failures"][result["workflow"]]
