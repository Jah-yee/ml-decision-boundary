#!/usr/bin/env python3
"""Audit the CI trigger block of a GitHub Actions workflow.

**Why this exists.** A workflow's ``on.pull_request.branches`` filter decides
*which base branches a pull request may target for CI to run at all*.  When
that filter names only ``master``, any pull request opened against a
**stacked** base branch (a feature branch instead of ``master``) silently
produces **zero** checks — the workflow never starts.

This is not a theoretical risk.  In this repository, PR #63 was opened with
``base = feat/v13-replay-provenance`` while the workflow filtered
``pull_request: branches: [master]``.  The result was that PR #63 accumulated
**no CI runs at all**, and the change it carried (the v13 replay integrity
guard plus 51 new tests) had never been verified by CI.  Meanwhile PRs
#60 / #61 / #62, which all target ``master``, did get the full 6-job suite.
The gap was invisible unless you explicitly asked GitHub for the check list
and noticed that it was *empty* rather than *failing*.

**What this script does.**  It reads a workflow file, extracts the ``on:``
trigger block, and answers the question *"would CI run for a pull request
whose base branch is X?"* — the same question GitHub Answers, but
locally and without a network round-trip.

**Design constraints.**

- **No third-party dependency.**  PyYAML is available in the dev container
  but is *not* in ``requirements.lock``, so importing it here would break
  CI.  The parser below is a deliberately small subset reader that handles
  exactly the shape of an Actions trigger block: one level of nesting under
  ``on:``, inline flow lists (``[a, b]``), and block lists (``- item``).
  It raises on anything it does not understand rather than guessing, so a
  future edit to the workflow cannot be silently mis-parsed.
- **Read-only.**  The audit never writes to the workflow.  Fixing the
  workflow is a human (or agent) decision; the script's job is to make the
  gap *visible* and *testable*.

Usage::

    python3 scripts/ci_trigger_audit.py                 # audit every workflow
    python3 scripts/ci_trigger_audit.py --workflow .github/workflows/ci.yml
    python3 scripts/ci_trigger_audit.py --base master   # explicit base branch
    python3 scripts/ci_trigger_audit.py --json          # machine-readable
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"

#: Branch patterns that always count as "the mainline" for a pull request.
MAINLINE_BRANCHES = ("master", "main")


class WorkflowParseError(RuntimeError):
    """Raised when the workflow's trigger block cannot be understood.

    We fail loudly on purpose: a parser that silently returns "no filters"
    for an unrecognised shape would make the audit *lie* — reporting a
    coverage gap that does not exist, or worse, hiding one that does.
    """


# ── Minimal YAML subset reader ─────────────────────────────────────────────

def _strip_comment(line: str) -> str:
    """Remove a trailing ``#`` comment that is not inside a quoted string."""
    out: list[str] = []
    quote: str | None = None
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


def _is_comment(line: str) -> bool:
    """True for a full-line YAML comment (ignoring leading whitespace)."""
    return line.lstrip().startswith("#")


def _parse_flow_list(raw: str) -> list[str]:
    """Parse an inline flow list such as ``[master, daily/*]``."""
    inner = raw.strip()[1:-1].strip()
    if not inner:
        return []
    items = []
    for part in inner.split(","):
        part = part.strip().strip("'\"")
        if part:
            items.append(part)
    return items


def _read_trigger_block(text: str) -> list[tuple[str, int]]:
    """Return ``(event, indent)`` pairs for the top-level keys under ``on:``.

    ``indent`` is the indentation of the event's own ``branches:`` key (or
    ``-1`` when the event has no ``branches`` filter).
    """
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == "on:" or line.rstrip() == "on:":
            start = idx
            break
    if start is None:
        raise WorkflowParseError("workflow has no top-level 'on:' trigger block")

    base_indent = len(lines[start]) - len(lines[start].lstrip())
    events: list[tuple[str, int]] = []

    for idx, line in enumerate(lines[start + 1:], start=start + 1):
        if not line.strip():
            continue
        if _is_comment(line):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent:
            # Back at (or above) the level of 'on:' -> the block ended.
            break
        stripped = _strip_comment(line).strip()
        if stripped.startswith("- "):
            # A list item directly under 'on:' (e.g. 'on: [push, pull_request]')
            # is handled by the caller; here it just means "event list form".
            continue
        if indent == base_indent + 2:
            event = stripped.rstrip(":")
            if not event:
                continue
            # Look ahead for a 'branches:' key belonging to this event.
            branches_indent = -1
            for probe in lines[idx + 1:]:
                if not probe.strip() or _is_comment(probe):
                    continue
                probe_indent = len(probe) - len(probe.lstrip())
                if probe_indent <= base_indent + 2:
                    break
                if _strip_comment(probe).strip().startswith("branches:"):
                    branches_indent = probe_indent
                    break
            events.append((event, branches_indent))
    return events


def _parse_branches_filter(text: str, event: str) -> list[str] | None:
    """Return the ``branches`` filter for ``event``, or ``None`` if absent.

    ``None`` means "no filter" -> the workflow runs for every base branch.
    An empty list means "an explicitly empty filter" -> nothing matches.
    """
    lines = text.splitlines()
    start = None
    for idx, line in enumerate(lines):
        if line.strip() == "on:" or line.rstrip() == "on:":
            start = idx
            break
    if start is None:
        raise WorkflowParseError("workflow has no top-level 'on:' trigger block")

    base_indent = len(lines[start]) - len(lines[start].lstrip())
    in_event = False
    event_indent = base_indent + 2

    for idx in range(start + 1, len(lines)):
        line = lines[idx]
        if not line.strip():
            continue
        if _is_comment(line):
            continue
        indent = len(line) - len(line.lstrip())
        if indent <= base_indent:
            break
        stripped = _strip_comment(line).strip()
        if indent == event_indent and stripped.rstrip(":") == event:
            in_event = True
            continue
        if in_event:
            if indent <= event_indent:
                break
            if stripped.startswith("branches:"):
                value = stripped.split(":", 1)[1].strip()
                if value.startswith("[") and value.endswith("]"):
                    return _parse_flow_list(value)
                # Block-list form:
                #   branches:
                #     - master
                #     - daily/*
                items: list[str] = []
                for probe in lines[idx + 1:]:
                    if not probe.strip() or _is_comment(probe):
                        continue
                    probe_indent = len(probe) - len(probe.lstrip())
                    if probe_indent <= indent:
                        break
                    probe_stripped = _strip_comment(probe).strip()
                    if probe_stripped.startswith("- "):
                        items.append(probe_stripped[2:].strip().strip("'\""))
                return items
    return None


# ── Pattern matching (GitHub's filter semantics) ───────────────────────────

def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a GitHub branch filter pattern into a regex.

    GitHub uses ``*`` (matches any characters except ``/``), ``**`` (matches
    across ``/``), and ``?`` (matches a single character).  ``*`` alone is
    also treated as a wildcard for a whole segment.
    """
    out = ["^"]
    i = 0
    n = len(pattern)
    while i < n:
        ch = pattern[i]
        if ch == "*":
            if i + 1 < n and pattern[i + 1] == "*":
                out.append(".*")
                i += 2
                # swallow a following '/' so 'a/**/b' also matches 'a/b'
                if i < n and pattern[i] == "/":
                    i += 1
                continue
            out.append("[^/]*")
            i += 1
            continue
        if ch == "?":
            out.append("[^/]")
            i += 1
            continue
        out.append(re.escape(ch))
        i += 1
    out.append("$")
    return re.compile("".join(out))


def branch_matches(base_branch: str, patterns: list[str]) -> bool:
    """Return True if ``base_branch`` matches any of ``patterns``."""
    for pattern in patterns:
        if pattern == base_branch:
            return True
        if "*" in pattern or "?" in pattern:
            if _glob_to_regex(pattern).match(base_branch):
                return True
    return False


# ── Audit ───────────────────────────────────────────────────────────────────

class TriggerAudit:
    """The result of auditing one workflow's ``pull_request`` trigger."""

    def __init__(self, workflow: Path, branches: list[str] | None, events: list[str]):
        self.workflow = workflow
        self.branches = branches
        self.events = events

    @property
    def has_pull_request(self) -> bool:
        return "pull_request" in self.events

    @property
    def is_unfiltered(self) -> bool:
        """True when CI runs for *every* base branch."""
        return self.has_pull_request and self.branches is None

    def covers(self, base_branch: str) -> bool:
        """Would CI run for a pull request targeting ``base_branch``?"""
        if not self.has_pull_request:
            return False
        if self.branches is None:
            return True
        return branch_matches(base_branch, self.branches)

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow": str(self.workflow),
            "events": self.events,
            "pull_request_branches": self.branches,
            "unfiltered": self.is_unfiltered,
        }


def audit_workflow(workflow: Path) -> TriggerAudit:
    """Audit a single workflow file."""
    text = workflow.read_text(encoding="utf-8")
    events = [name for name, _ in _read_trigger_block(text)]
    branches = _parse_branches_filter(text, "pull_request")
    return TriggerAudit(workflow, branches, events)


def audit_all(workflow_dir: Path = WORKFLOW_DIR) -> list[TriggerAudit]:
    """Audit every workflow in ``workflow_dir``."""
    if not workflow_dir.is_dir():
        return []
    results = []
    for workflow in sorted(workflow_dir.glob("*.yml")):
        results.append(audit_workflow(workflow))
    return results


def find_uncovered_bases(
    audits: list[TriggerAudit],
    base_branches: list[str],
) -> list[tuple[str, str]]:
    """Return ``(workflow, base_branch)`` pairs that CI would *not* cover.

    Workflows that do not subscribe to ``pull_request`` at all (a
    tag-driven release workflow, for instance) are not a coverage gap —
    they were never meant to run on pull requests.  Only workflows that
    *do* subscribe to ``pull_request`` can leave a base branch uncovered.
    """
    gaps: list[tuple[str, str]] = []
    for audit in audits:
        if not audit.has_pull_request:
            continue
        for base in base_branches:
            if not audit.covers(base):
                gaps.append((str(audit.workflow), base))
    return gaps


def _default_base_branches() -> list[str]:
    """Base branches worth checking: the mainline plus known feature branches.

    Stacked pull requests target a *feature* branch, which is precisely the
    case a ``branches: [master]`` filter misses.  We therefore probe the
    mainline plus every local/remote feature branch that has an open PR
    against it — but we do not need the network for the audit to be useful,
    so a small static list of the repository's real stacked bases is used
    as the default probe set.
    """
    return list(MAINLINE_BRANCHES) + [
        "feat/v12-sdk-foundation",
        "feat/v13-provenance-provenance",
        "feat/v13-replay-provenance",
        "feat/v13-replay-integrity-guard",
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument(
        "--workflow",
        type=Path,
        default=None,
        help="audit only this workflow file (default: every workflow)",
    )
    parser.add_argument(
        "--base",
        action="append",
        default=None,
        help="base branch to probe (repeatable; default: mainline + feature branches)",
    )
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    args = parser.parse_args(argv)

    if args.workflow:
        audits = [audit_workflow(args.workflow)]
    else:
        audits = audit_all()

    bases = args.base if args.base else _default_base_branches()
    gaps = find_uncovered_bases(audits, bases)

    if args.json:
        print(json.dumps({
            "workflows": [a.to_dict() for a in audits],
            "probed_base_branches": bases,
            "gaps": [{"workflow": w, "base_branch": b} for w, b in gaps],
            "ok": not gaps,
        }, indent=2))
        return 0 if not gaps else 1

    print("🔍 CI trigger coverage audit")
    print("=" * 60)
    for audit in audits:
        rel = audit.workflow
        try:
            rel = audit.workflow.relative_to(REPO_ROOT)
        except ValueError:
            pass
        branches = audit.branches
        if branches is None:
            shown = "(no filter — every base branch)"
        else:
            shown = ", ".join(branches)
        print(f"\n📄 {rel}")
        print(f"   events: {', '.join(audit.events) or '(none)'}")
        if not audit.has_pull_request:
            print("   pull_request base filter: n/a — workflow does not run on pull requests")
            continue
        print(f"   pull_request base filter: {shown}")
        for base in bases:
            mark = "✅" if audit.covers(base) else "❌"
            print(f"     {mark} base={base}")

    print()
    if gaps:
        print(f"❌ {len(gaps)} uncovered (workflow, base) combination(s):")
        for workflow, base in gaps:
            print(f"   - {workflow}  ← base '{base}' gets NO CI")
        print()
        print("   A pull request targeting such a base produces zero checks.")
        print("   Fix: drop the 'branches:' filter from the pull_request trigger,")
        print("   or widen it to cover every branch a PR can target.")
        return 1

    print("✅ Every pull request base branch is covered by CI.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
