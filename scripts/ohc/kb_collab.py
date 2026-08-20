"""Knowledge graph collaboration module — authorship tracking & draft promotion.

Implements the knowledge collaboration mode:
- Drafts auto-fill authors from git config
- Main editor promotes drafts to official entries, carrying over authors
- Merging a draft into an existing entry appends author as 2nd/3rd contributor
- Change log goes to .md only; .kv only stores the author/email list

Usage:
    from .kb_collab import promote_draft, merge_draft_to_entry

    # Promote a new draft to official entry
    promote_draft("knowledge/drafts/E081-draft-42FF.kv",
                  "knowledge/graph/E059.kv")

    # Merge a draft into an existing entry (adds 2nd author)
    merge_draft_to_entry("knowledge/drafts/E080-draft-0BE3.kv",
                         "E035", "knowledge/graph/")
"""
from __future__ import annotations

import os
import re
import subprocess
from datetime import date
from pathlib import Path
from typing import Optional


def _parse_kv(path: str) -> dict[str, str]:
    """Minimal KV parser."""
    data: dict[str, str] = {}
    current_key: Optional[str] = None
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip().startswith("#"):
                continue
            m = re.match(r'^([a-z_]+):\s*(.*)', line)
            if m:
                current_key = m.group(1)
                data[current_key] = m.group(2).strip()
            elif current_key and line.startswith(" "):
                data[current_key] += " " + line.strip()
    return data


def _get_git_author() -> str:
    """Get author from git config."""
    try:
        name = subprocess.check_output(
            ["git", "config", "user.name"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        email = subprocess.check_output(
            ["git", "config", "user.email"], text=True, stderr=subprocess.DEVNULL
        ).strip()
        if name and email:
            return f"{name} <{email}>"
    except Exception:
        pass
    return ""


def _get_git_commit_short() -> str:
    """Get current short commit SHA."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return ""


def promote_draft(
    draft_path: str,
    official_path: str,
    *,
    source_pr: str = "",
) -> str:
    """Promote a draft to an official knowledge graph entry.

    - Carries over the authors field from the draft
    - Sets draft: false
    - Fills source_commit from current git HEAD
    - Returns the official path

    Args:
        draft_path: Path to the draft .kv file
        official_path: Target path for the official .kv file
        source_pr: PR number (if known)

    Returns:
        The official path on success
    """
    draft = Path(draft_path)
    official = Path(official_path)

    if not draft.exists():
        raise FileNotFoundError(f"Draft not found: {draft}")

    content = draft.read_text(encoding="utf-8")

    # Update metadata fields
    today = date.today().isoformat()
    content = re.sub(r'draft:\s*true', 'draft: false', content)
    content = re.sub(r'last_updated:.*', f'last_updated: {today}', content)

    # Fill source_commit if empty
    commit = _get_git_commit_short()
    if commit and 'source_commit:' in content:
        content = re.sub(
            r'source_commit:\s*$',
            f'source_commit: {commit}',
            content, flags=re.MULTILINE,
        )

    # Fill source_pr if provided
    if source_pr and 'source_pr:' in content:
        content = re.sub(
            r'source_pr:\s*$',
            f'source_pr: {source_pr}',
            content, flags=re.MULTILINE,
        )

    # Ensure authors field exists (fill from git if missing)
    if 'authors:' not in content or re.search(r'authors:\s*$', content):
        author = _get_git_author()
        if author:
            content = re.sub(
                r'authors:\s*$',
                f'authors: {author}',
                content, flags=re.MULTILINE,
            )

    official.write_text(content, encoding="utf-8")
    return str(official)


def merge_draft_to_entry(
    draft_path: str,
    entry_id: str,
    graph_dir: str,
    *,
    change_description: str = "",
) -> str:
    """Merge a draft into an existing official entry (adds 2nd/3rd author).

    - Reads authors from both draft and official entry
    - Appends draft author to official entry's authors list
    - Adds a change log entry to the .md doc file (not to .kv)
    - Returns the updated official path

    Args:
        draft_path: Path to the draft .kv file
        entry_id: Official entry ID (e.g., "E035")
        graph_dir: Path to knowledge/graph/ directory
        change_description: Description of what was added/changed

    Returns:
        The official .kv path on success
    """
    draft = Path(draft_path)
    official_kv = Path(graph_dir) / f"{entry_id}.kv"

    if not draft.exists():
        raise FileNotFoundError(f"Draft not found: {draft}")
    if not official_kv.exists():
        raise FileNotFoundError(f"Official entry not found: {official_kv}")

    # Read authors from both
    draft_data = _parse_kv(str(draft))
    official_data = _parse_kv(str(official_kv))

    draft_authors = draft_data.get("authors", "").strip()
    official_authors = official_data.get("authors", "").strip()

    if not draft_authors:
        draft_authors = _get_git_author()

    if not draft_authors:
        return str(official_kv)  # Nothing to merge

    # Append author if not already in list
    if draft_authors not in official_authors:
        if official_authors:
            new_authors = f"{official_authors}, {draft_authors}"
        else:
            new_authors = draft_authors

        content = official_kv.read_text(encoding="utf-8")
        content = re.sub(
            r'authors:.*',
            f'authors: {new_authors}',
            content, count=1,
        )

        # Update last_updated
        today = date.today().isoformat()
        content = re.sub(r'last_updated:.*', f'last_updated: {today}', content)

        official_kv.write_text(content, encoding="utf-8")

    # Add change log to .md doc file (not to .kv)
    doc_file = official_data.get("doc_file", "").strip()
    if doc_file:
        doc_path = Path(graph_dir).parent / doc_file
        if not doc_path.exists():
            # Create if doesn't exist
            doc_path.parent.mkdir(parents=True, exist_ok=True)
            doc_path.write_text(f"# {entry_id} — Knowledge Entry\n\n", encoding="utf-8")

        _add_changelog(str(doc_path), draft_authors, change_description or "补充场景/方案")

    return str(official_kv)


def _add_changelog(md_path: str, author: str, change: str) -> None:
    """Add a change log entry to a .md doc file.

    The change log is only in the markdown doc, not in the .kv file.
    Format:
        ## Change Log
        - 2026-06-30 Author <email>: description
    """
    path = Path(md_path)
    content = path.read_text(encoding="utf-8") if path.exists() else ""

    today = date.today().isoformat()
    entry = f"- {today} {author}: {change}"

    if "## Change Log" in content:
        # Append to existing change log
        content = content.replace(
            "## Change Log",
            f"## Change Log\n{entry}",
        )
    else:
        # Create new change log section
        content = content.rstrip() + f"\n\n## Change Log\n{entry}\n"

    path.write_text(content, encoding="utf-8")


def list_contributors(graph_dir: str) -> dict[str, list[str]]:
    """List all contributors and their entries.

    Returns:
        {"Author <email>": ["E001", "E035", ...], ...}
    """
    contributors: dict[str, list[str]] = {}
    gdir = Path(graph_dir)

    for f in sorted(gdir.glob("E*.kv")):
        data = _parse_kv(str(f))
        authors = data.get("authors", "").strip()
        eid = data.get("id", f.stem)

        if not authors:
            continue

        for author in authors.split(","):
            author = author.strip()
            if author:
                contributors.setdefault(author, []).append(eid)

    return contributors
