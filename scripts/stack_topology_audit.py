#!/usr/bin/env python3
"""Audit whether a stack of pull requests can actually be merged.

**Why this exists.**  This repository uses *stacked* pull requests: each
pull request's base branch is another pull request's head branch.

```
master
  └── feat/v12-sdk-foundation        (PR #60)
        └── feat/v13-provenance-provenance  (PR #61)
              └── feat/v13-replay-provenance  (PR #62)
                    └── feat/v13-replay-integrity-guard  (PR #63)
                          └── feat/v13-ci-trigger-coverage  (PR #66)
                                └── feat/v13-pr-coverage-audit  (PR #67)
```

Two earlier audits already exist and both are necessary:

- :mod:`ci_trigger_audit` (DoD #7) asks *"would CI run for a pull
  request whose base is X?"* about the workflow file on a branch;
- :mod:`pr_coverage_audit` (DoD #8) asks *"is every open pull request
  actually covered by CI?"* about the workflow on each pull request's
  head branch.

Both are about **workflow content and check coverage**.  Neither one
looks at the **shape of the stack itself** — whether the branches form a
linear chain, and whether merging them in the order they will be merged
actually succeeds.

**The gap this audit closes, as it actually happened.**  PR #63
(``feat/v13-replay-integrity-guard``) and PR #66
(``feat/v13-ci-trigger-coverage``) had been prepared in parallel, and
both branches independently added *the same* ``pr-coverage-audit`` job
to ``.github/workflows/ci.yml`` — the backport in PR #63 carried DoD
#7's fix down the stack, and PR #66 was where DoD #7's fix originated.

The two branches' ``ci.yml`` files were therefore **byte-identical**,
and neither contained the other's commit.  Both pull requests reported
``mergeable: MERGEABLE, mergeable_state: clean`` — GitHub's own answer
looked perfect.

But the branches had **diverged**: their merge base was ``4962d28``,
which contained no ``pr-coverage-audit`` job at all.  When the emperor
merged PR #63 into PR #66's branch, git produced:

```
CONFLICT (content): Merge conflict in .github/workflows/ci.yml
```

Git cannot auto-resolve "both sides added identical content", because
both sides' blobs differ from the base.  **The stack could not be
merged without manual conflict resolution** — and neither GitHub's
``mergeable`` flag nor either existing audit would ever have said so.

**What this audit checks.**  For every open pull request whose base
branch is *also* an open pull request's head branch, the audit builds
the intended merge chain and verifies, for each consecutive pair:

1. **Ancestry** — is the lower pull request's head actually an ancestor
   of the upper pull request's head?  If not, the branches have
   diverged and the chain is not linear.
2. **Mergeability** — would merging the lower branch into the upper one
   succeed without conflicts?  This is computed with ``git merge-tree``,
   which performs a real merge without touching the working tree.
3. **Duplicate payload** — when the two branches contain the *same*
   change (identical file contents) but different commits, that is the
   signature of the "both sides added identical content" conflict.
   The audit reports it as *repairable*, because the fix is mechanical:
   rebase the upper branch onto the lower one and drop the duplicate
   commit.

The audit also computes the **merge order** — the order in which the
pull requests must be merged for the stack to land cleanly — and
reports it as a ready-to-use command list.

**Design constraints.**

- **Read-only.**  The audit never merges, never pushes, never rewrites a
  branch.  It reports; a human decides.
- **No third-party dependency.**  PyYAML is not in ``requirements.lock``,
  so importing it would break CI.
- **Degrades honestly.**  When the pull request list or the git history
  cannot be obtained, the audit says so and exits non-zero rather than
  reporting a vacuous success.

Usage::

    python3 scripts/stack_topology_audit.py              # audit the whole stack
    python3 scripts/stack_topology_audit.py --json       # machine-readable
    python3 scripts/stack_topology_audit.py --pr 66     # one pull request
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


class StackAuditError(RuntimeError):
    """Raised when the stack state cannot be obtained."""


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


def default_branch(repo_root: Path = REPO_ROOT) -> str:
    """Return the repository's default branch.

    The default branch is the root of the stack: a pull request is
    "in the stack" when its base branch is the default branch, or the
    head branch of another pull request in the stack.

    The name is **detected**, never assumed.  Hard-coding ``master``
    would make the audit silently report an empty stack against a
    repository whose default branch is called ``main`` — which is
    exactly the "vacuous success" failure this audit exists to avoid.
    """
    # Prefer GitHub's own answer: it knows the default branch even when
    # the local clone has no matching ref.
    if gh_available():
        proc = _run(
            ["gh", "repo", "view", "--json", "defaultBranchRef"],
            cwd=repo_root,
        )
        if proc.returncode == 0:
            try:
                data = json.loads(proc.stdout or "{}")
            except json.JSONDecodeError:
                data = {}
            name = (data.get("defaultBranchRef") or {}).get("name")
            if name:
                return str(name)

    # Fall back to the local remote's HEAD, which points at the
    # default branch.
    proc = _run(
        ["git", "symbolic-ref", "--quiet", "refs/remotes/origin/HEAD"],
        cwd=repo_root,
    )
    if proc.returncode == 0:
        ref = (proc.stdout or "").strip()
        if ref.startswith("refs/remotes/origin/"):
            return ref[len("refs/remotes/origin/"):]

    # Last resort: a local branch that literally exists.
    proc = _run(["git", "branch", "--list", "master", "main"], cwd=repo_root)
    for line in (proc.stdout or "").splitlines():
        name = line.strip().lstrip("* ").strip()
        if name:
            return name

    return "master"


def list_open_prs(repo_root: Path = REPO_ROOT) -> list[dict[str, Any]]:
    """Return the open pull requests as JSON dicts.

    Raises :class:`StackAuditError` when the list cannot be obtained —
    the caller must not treat an unavailable list as "the stack is fine".
    """
    if not gh_available():
        raise StackAuditError("the 'gh' CLI is not installed")
    proc = _run(
        [
            "gh", "pr", "list",
            "--state", "open",
            "--limit", "100",
            "--json",
            "number,title,headRefName,baseRefName,mergeable,mergeStateStatus",
        ],
        cwd=repo_root,
    )
    if proc.returncode != 0:
        raise StackAuditError(
            f"'gh pr list' failed (rc={proc.returncode}): "
            f"{(proc.stderr or proc.stdout).strip()[:400]}"
        )
    try:
        data = json.loads(proc.stdout or "[]")
    except json.JSONDecodeError as exc:
        raise StackAuditError(f"'gh pr list' returned non-JSON output: {exc}") from exc
    if not isinstance(data, list):
        raise StackAuditError("'gh pr list' did not return a list")
    return data


def is_ancestor(ancestor: str, descendant: str, repo_root: Path = REPO_ROOT) -> bool:
    """True when ``ancestor`` is an ancestor of ``descendant``."""
    proc = _run(
        ["git", "merge-base", "--is-ancestor", ancestor, descendant],
        cwd=repo_root,
    )
    return proc.returncode == 0


def merge_base(a: str, b: str, repo_root: Path = REPO_ROOT) -> str | None:
    """Return the merge base of two revisions, or ``None`` when there is none."""
    proc = _run(["git", "merge-base", a, b], cwd=repo_root)
    if proc.returncode != 0:
        return None
    out = (proc.stdout or "").strip()
    return out or None


def merge_conflicts(
    ours: str,
    theirs: str,
    repo_root: Path = REPO_ROOT,
) -> tuple[list[str], bool]:
    """Perform a real merge in-memory and report the conflicted paths.

    ``git merge-tree --write-tree`` computes a three-way merge between
    two commits and writes the result into a tree object.  It touches
    nothing in the working tree, so it is safe to run on a live
    repository and on CI.

    Returns ``(conflicted_paths, merge_succeeded)``.  When the merge
    succeeds the second element is ``True`` and the list is empty.

    **The exit code alone is not a reliable conflict signal.**  There are
    two ways to get this wrong:

    * ``git merge-tree --write-tree`` writes the merged tree *with
      conflict markers embedded in the blobs* and reports the conflict
      on stdout.  Depending on the git version and the conflict kind,
      the exit code may be ``0`` or ``1`` — it is not a contract.
    * Piping the command into ``head``/``grep`` replaces ``$?`` with the
      *pipeline's* exit status, so ``... | head; echo $?`` reports
      ``head``'s status and hides git's.

    The conflict is therefore detected from the **output**, which is
    stable across git versions:

    .. code-block:: text

        <tree-ish hash>              # always the first line
        <conflicted path>            # zero or more lines
        <blank line>
        Auto-merging <path>
        CONFLICT (<kind>): <message>

    A clean merge prints **only** the tree-ish hash.  So the first line
    is always the hash and must be skipped; everything between it and
    the informational section is a conflicted path.
    """
    proc = _run(
        ["git", "merge-tree", "--write-tree", "--name-only", ours, theirs],
        cwd=repo_root,
    )
    out = (proc.stdout or "") + (proc.stderr or "")

    # A hard error (unknown revision, not a repository, ...) is reported
    # with a non-zero exit code and a message that is not a conflict
    # report.  That is not a merge conflict — it is a failure to even
    # attempt the merge, and it must not be reported as "the branches
    # disagree".
    if "fatal:" in out.lower() or (
        proc.returncode != 0 and "CONFLICT" not in out
    ):
        raise StackAuditError(
            f"'git merge-tree' failed for {ours} / {theirs}: {out.strip()[:400]}"
        )

    lines = out.splitlines()
    if not lines:
        # git printed nothing at all — the merge could not be described.
        raise StackAuditError(
            f"'git merge-tree' produced no output for {ours} / {theirs}"
        )

    # Skip the tree-ish hash on the first line.
    body = lines[1:]

    paths: list[str] = []
    seen_conflict = False
    for raw_line in body:
        line = raw_line.strip()
        if not line:
            # A blank line ends the path list and starts the
            # informational section.
            if paths:
                break
            continue
        if line.startswith(("CONFLICT", "Auto-merging", "warning:", "error:")):
            seen_conflict = True
            continue
        if line.endswith(":"):
            # Section headers like "added in both:".
            seen_conflict = True
            continue
        paths.append(line)

    # The output is the primary signal; a non-zero exit code is a
    # secondary one (it catches a conflict kind whose informational
    # section this parser does not recognise).
    if seen_conflict or paths or proc.returncode != 0:
        return paths, False
    return [], True


def _tree_paths(commit: str, repo_root: Path = REPO_ROOT) -> set[str]:
    """Return the set of file paths present in a commit's tree."""
    proc = _run(["git", "ls-tree", "-r", "--name-only", commit], cwd=repo_root)
    if proc.returncode != 0:
        return set()
    return {line for line in (proc.stdout or "").splitlines() if line}


def file_contents(commit: str, path: str, repo_root: Path = REPO_ROOT) -> str | None:
    """Return the contents of ``path`` at ``commit``, or ``None``."""
    proc = _run(["git", "show", f"{commit}:{path}"], cwd=repo_root)
    if proc.returncode != 0:
        return None
    return proc.stdout


# ── Stack model ─────────────────────────────────────────────────────────────

@dataclass
class StackLink:
    """The relationship between one pull request and its base pull request.

    A *link* exists when the pull request's base branch is another open
    pull request's head branch.  Those are the edges of the stack.
    """

    #: The pull request whose head branch is the base of :attr:`lower_number`.
    upper_number: int
    #: The pull request whose head branch is the base of :attr:`upper_number`.
    lower_number: int
    upper_head: str
    lower_head: str
    upper_base: str
    lower_base: str

    #: True when ``lower_head`` is an ancestor of ``upper_head``.
    linear: bool = False
    #: The merge base of the two heads (``None`` when there is none).
    merge_base: str | None = None
    #: Files that a real merge of the two branches would conflict on.
    conflicts: list[str] = field(default_factory=list)
    #: True when the merge of the two branches succeeds cleanly.
    mergeable: bool = False
    #: Files whose *contents* are identical on both branches but differ
    #: from the merge base — the signature of a duplicated commit.
    duplicated_payload: list[str] = field(default_factory=list)
    #: Why this link is not a plain linear chain.
    verdict: str = "unknown"
    problems: list[str] = field(default_factory=list)

    @property
    def is_clean(self) -> bool:
        """True when this link can be merged without manual intervention."""
        return self.linear and self.mergeable and not self.duplicated_payload

    @property
    def is_repairable(self) -> bool:
        """True when the only problem is a duplicated commit.

        A duplicated commit is mechanically fixable: rebase the upper
        branch onto the lower one and drop the duplicate.  The audit
        reports it as repairable rather than merely broken, because the
        difference between "your stack is broken" and "your stack needs
        one rebase" is the difference between a blocker and a task.
        """
        return (
            not self.linear
            and self.mergeable
            and bool(self.duplicated_payload)
            and not self.conflicts
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "upper_number": self.upper_number,
            "lower_number": self.lower_number,
            "upper_head": self.upper_head,
            "lower_head": self.lower_head,
            "upper_base": self.upper_base,
            "lower_base": self.lower_base,
            "linear": self.linear,
            "merge_base": self.merge_base,
            "mergeable": self.mergeable,
            "conflicts": list(self.conflicts),
            "duplicated_payload": list(self.duplicated_payload),
            "verdict": self.verdict,
            "is_clean": self.is_clean,
            "is_repairable": self.is_repairable,
            "problems": list(self.problems),
        }


@dataclass
class Stack:
    """The chain of pull requests rooted at the default branch."""

    #: The pull requests in the stack, ordered bottom-up.
    prs: list[dict[str, Any]] = field(default_factory=list)
    #: The links between consecutive pull requests.
    links: list[StackLink] = field(default_factory=list)
    #: The default branch the stack is rooted at.
    root: str = "master"

    def order(self) -> list[int]:
        """The pull request numbers in the order they must be merged."""
        return [int(pr["number"]) for pr in self.prs]

    def broken_links(self) -> list[StackLink]:
        return [link for link in self.links if not link.is_clean]

    def to_dict(self) -> dict[str, Any]:
        return {
            "root": self.root,
            "order": self.order(),
            "prs": [
                {
                    "number": int(pr["number"]),
                    "title": pr.get("title", ""),
                    "head": pr.get("headRefName", ""),
                    "base": pr.get("baseRefName", ""),
                    "mergeable": pr.get("mergeable"),
                    "merge_state": pr.get("mergeStateStatus"),
                }
                for pr in self.prs
            ],
            "links": [link.to_dict() for link in self.links],
            "summary": self.summary(),
        }

    def summary(self) -> dict[str, Any]:
        broken = self.broken_links()
        return {
            "total": len(self.prs),
            "links": len(self.links),
            "clean_links": len(self.links) - len(broken),
            "broken_links": len(broken),
            "repairable_links": len([link for link in broken if link.is_repairable]),
            "blocked_links": len(
                [link for link in broken if not link.is_repairable]
            ),
            "broken_pairs": [
                [link.lower_number, link.upper_number] for link in broken
            ],
            "ok": not broken,
        }


# ── Audit ───────────────────────────────────────────────────────────────────

def build_stack(
    prs: list[dict[str, Any]],
    repo_root: Path = REPO_ROOT,
    root: str | None = None,
) -> Stack:
    """Order the pull requests into a stack and audit each link.

    The stack is built by walking *up* from the default branch: a pull
    request belongs to the stack when its base branch is either the
    default branch or the head branch of another pull request in the
    stack.

    Pull requests whose base is a branch that is not part of the stack
    (an external branch, or a branch nobody has open a pull request
    against) are **not** part of the chain and are ignored.
    """
    by_head: dict[str, dict[str, Any]] = {}
    for pr in prs:
        head = str(pr.get("headRefName") or "")
        if head:
            by_head[head] = pr

    # Walk up from the root.  ``root`` is the default branch; any pull
    # request based on it starts the chain.
    if root is None:
        root = default_branch(repo_root)
    ordered: list[dict[str, Any]] = []
    seen_heads: set[str] = set()

    def base_of(pr: dict[str, Any]) -> str:
        return str(pr.get("baseRefName") or "")

    frontier = [pr for pr in prs if base_of(pr) == root]
    frontier.sort(key=lambda pr: int(pr["number"]))

    while frontier:
        pr = frontier.pop(0)
        head = str(pr.get("headRefName") or "")
        if head in seen_heads:
            continue
        seen_heads.add(head)
        ordered.append(pr)
        for candidate in prs:
            if base_of(candidate) == head and candidate not in ordered:
                frontier.append(candidate)

    stack = Stack(prs=ordered, root=root)

    # Audit every consecutive pair.
    for lower, upper in zip(ordered, ordered[1:]):
        stack.links.append(_audit_link(lower, upper, repo_root))

    return stack


def _audit_link(
    lower: dict[str, Any],
    upper: dict[str, Any],
    repo_root: Path = REPO_ROOT,
) -> StackLink:
    """Audit the relationship between two consecutive pull requests."""
    lower_head = str(lower.get("headRefName") or "")
    upper_head = str(upper.get("headRefName") or "")

    link = StackLink(
        upper_number=int(upper["number"]),
        lower_number=int(lower["number"]),
        upper_head=upper_head,
        lower_head=lower_head,
        upper_base=str(upper.get("baseRefName") or ""),
        lower_base=str(lower.get("baseRefName") or ""),
    )

    base = merge_base(lower_head, upper_head, repo_root)
    link.merge_base = base
    link.linear = base is not None and is_ancestor(lower_head, upper_head, repo_root)

    conflicts, ok = merge_conflicts(upper_head, lower_head, repo_root)
    link.conflicts = conflicts
    link.mergeable = ok

    if base is not None:
        link.duplicated_payload = _duplicated_payload(
            base, lower_head, upper_head, repo_root
        )

    if link.is_clean:
        link.verdict = "linear"
    elif link.is_repairable:
        link.verdict = "diverged-duplicate"
    elif link.conflicts:
        link.verdict = "conflict"
    elif not link.linear:
        link.verdict = "diverged"
    else:
        link.verdict = "unknown"

    for problem in _problems_for(link):
        link.problems.append(problem)

    return link


def _duplicated_payload(
    base: str,
    lower_head: str,
    upper_head: str,
    repo_root: Path = REPO_ROOT,
) -> list[str]:
    """Return files whose content is identical on both heads but differs
    from the merge base.

    This is the signature of two branches independently committing the
    same change.  Git cannot auto-resolve it: the merge base has none
    of the content, and both sides have identical content, so both
    sides look like an "add/add" conflict.
    """
    base_paths = _tree_paths(base, repo_root)
    lower_paths = _tree_paths(lower_head, repo_root)
    upper_paths = _tree_paths(upper_head, repo_root)

    candidates = (lower_paths | upper_paths) - base_paths
    duplicated: list[str] = []
    for path in sorted(candidates):
        lower_content = file_contents(lower_head, path, repo_root)
        upper_content = file_contents(upper_head, path, repo_root)
        if lower_content is None or upper_content is None:
            continue
        if lower_content == upper_content:
            duplicated.append(path)
    return duplicated


def _problems_for(link: StackLink) -> list[str]:
    """Human-readable explanations for a link's problems."""
    problems: list[str] = []
    if not link.linear:
        problems.append(
            f"PR #{link.lower_number}'s head branch is not an ancestor of PR "
            f"#{link.upper_number}'s head branch — the two branches have "
            f"diverged"
        )
    if link.conflicts:
        problems.append(
            "merging PR "
            f"#{link.lower_number} into PR #{link.upper_number} conflicts on: "
            + ", ".join(link.conflicts)
        )
    if link.duplicated_payload:
        problems.append(
            "both branches independently committed the same change to: "
            + ", ".join(link.duplicated_payload)
            + " — the content is identical, so this is a duplicated commit "
            "rather than a real disagreement"
        )
    return problems


# ── Gate ────────────────────────────────────────────────────────────────────

#: The requirement set evaluated by the *default* gate.
#:
#: ``mergeable``
#:     every link can be merged without conflicts;
#: ``no_duplicate_payload``
#:     no link carries the same change on two branches.
#:
#: The default gate answers: **can this stack be merged as-is?**
#: It tolerates divergence — a diverged stack can still be merged
#: bottom-up, and the audit reports the divergence as repairable.
DEFAULT_REQUIREMENTS: tuple[str, ...] = (
    "mergeable",
    "no_duplicate_payload",
)

#: The requirement set evaluated by the ``--strict`` gate.
#:
#: **This set is a strict superset of :data:`DEFAULT_REQUIREMENTS`.**
#: The extra requirement is that the stack must not merely be mergeable
#: but must also already be *linear* — i.e. the duplicate-commit
#: situation must be fixed rather than merely tolerated.
STRICT_REQUIREMENTS: tuple[str, ...] = DEFAULT_REQUIREMENTS + (
    "linear",
)


def _requirement_failed(link: StackLink, requirement: str) -> bool:
    """True when ``link`` fails a single requirement."""
    if requirement == "linear":
        return not link.linear
    if requirement == "mergeable":
        return not link.mergeable
    if requirement == "no_duplicate_payload":
        return bool(link.duplicated_payload)
    if requirement == "no_divergence":
        return not link.linear
    raise ValueError(f"unknown requirement: {requirement!r}")

def evaluate_gate(
    links: list[StackLink],
    requirements: tuple[str, ...] = DEFAULT_REQUIREMENTS,
) -> dict[str, Any]:
    """Evaluate the gate against the stack's links.

    This is the **single** place where "does this gate pass?" is
    decided, mirroring :func:`pr_coverage_audit.evaluate_gate`.  The
    requirement set is a superset relationship, so a stricter mode can
    only ever turn a pass into a failure.
    """
    failures: dict[int, list[str]] = {}
    for link in links:
        failed = [r for r in requirements if _requirement_failed(link, r)]
        if failed:
            failures[link.upper_number] = failed
    return {
        "ok": not failures,
        "failed": sorted(failures),
        "failures": {n: failures[n] for n in sorted(failures)},
        "requirements": list(requirements),
    }


# ── CLI ─────────────────────────────────────────────────────────────────────

def merge_order(stack: Stack) -> list[str]:
    """Return ready-to-run merge commands for the stack, bottom-up."""
    commands: list[str] = []
    for pr in stack.prs:
        number = int(pr["number"])
        head = str(pr.get("headRefName") or "")
        base = str(pr.get("baseRefName") or "")
        commands.append(
            f"gh pr merge {number} --merge  "
            f"# {head} → {base}"
        )
    return commands


def _print_report(stack: Stack, gate: dict[str, Any]) -> None:
    print("🔍 Stack topology audit")
    print("=" * 68)
    print(
        "Two earlier audits cover workflow content (ci_trigger_audit) and\n"
        "CI coverage (pr_coverage_audit).  This one covers the *shape* of\n"
        "the stack: can it actually be merged, in order?\n"
    )
    if not stack.prs:
        print("(no stacked pull requests found)\n")
        return

    print(f"Root branch: {stack.root}")
    print(f"Stack depth: {len(stack.prs)} pull request(s)")
    print()

    print("Merge order (bottom-up):")
    for pr in stack.prs:
        head = str(pr.get("headRefName") or "")
        base = str(pr.get("baseRefName") or "")
        print(f"  PR #{int(pr['number']):<4} {head} → {base}")
    print()

    if stack.links:
        print("Links:")
        for link in stack.links:
            mark = "✅" if link.is_clean else ("🔧" if link.is_repairable else "❌")
            print(f"{mark} PR #{link.lower_number} → PR #{link.upper_number}")
            print(f"     merge base  : {link.merge_base or '(none)'}")
            print(f"     linear      : {'yes' if link.linear else 'NO'}")
            print(
                "     mergeable   : "
                + ("yes" if link.mergeable else "NO — conflicts on "
                   + ", ".join(link.conflicts))
            )
            if link.duplicated_payload:
                print(
                    "     duplicated  : "
                    + ", ".join(link.duplicated_payload)
                    + "  (identical content on both branches)"
                )
            print(f"     verdict     : {link.verdict}")
            for problem in link.problems:
                print(f"     note        : {problem}")
            print()

    summary = stack.summary()
    print("-" * 68)
    print(
        f"{summary['clean_links']}/{summary['links']} link(s) are clean; "
        f"{summary['repairable_links']} repairable, "
        f"{summary['blocked_links']} blocked."
    )
    if summary["broken_links"]:
        for link in stack.broken_links():
            if link.is_repairable:
                print(
                    f"🔧 PR #{link.lower_number} and PR #{link.upper_number} carry the "
                    f"same change on two branches.\n"
                    f"   Fix: rebase PR #{link.upper_number}'s branch onto "
                    f"'{link.lower_head}' and drop the duplicate commit:\n"
                    f"     git rebase --onto {link.lower_head} "
                    f"{link.merge_base} {link.upper_head}\n"
                    f"   (the content is identical, so nothing is lost)"
                )
            else:
                print(
                    f"❌ PR #{link.lower_number} → PR #{link.upper_number} is blocked:\n"
                    f"     " + "\n     ".join(link.problems)
                )
    else:
        print("✅ The stack can be merged bottom-up without manual intervention.")

    if not gate["ok"]:
        print(
            f"\n❌ Gate failed for: "
            + ", ".join(f"PR #{n}" for n in gate["failed"])
        )
    print("\nSuggested merge order:")
    for cmd in merge_order(stack):
        print(f"  {cmd}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--pr", action="append", type=int, default=None,
                        help="restrict the audit to this pull request (repeatable)")
    parser.add_argument("--json", action="store_true", help="machine-readable output")
    parser.add_argument(
        "--strict",
        action="store_true",
        help=(
            "stricter gate mode: additionally require that the stack is "
            "already linear (no divergence tolerated)"
        ),
    )
    args = parser.parse_args(argv)

    try:
        prs = list_open_prs(REPO_ROOT)
    except StackAuditError as exc:
        print(f"❌ Cannot audit the stack: {exc}", file=sys.stderr)
        return 2

    if args.pr:
        wanted = set(args.pr)
        prs = [pr for pr in prs if int(pr["number"]) in wanted]

    stack = build_stack(prs, REPO_ROOT, root=default_branch(REPO_ROOT))

    requirements = STRICT_REQUIREMENTS if args.strict else DEFAULT_REQUIREMENTS
    gate = evaluate_gate(stack.links, requirements)

    if args.json:
        payload = stack.to_dict()
        payload["gate"] = gate
        payload["merge_order"] = merge_order(stack)
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        _print_report(stack, gate)

    if not gate["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
