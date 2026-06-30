"""Data models and parsers for knowledge graph (KV, TSV, Principles).

Only uses Python standard library.
"""
from __future__ import annotations

import csv
import keyword
import os
import re
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Optional

# Valid KV field name: starts with lowercase letter, contains only lowercase
# letters, digits, and underscores.  Rejects Python code tokens like
# "except MemoryError", "print('Mode", etc.  Also used to skip Python
# keywords (try, import, …) that happen to look like valid identifiers.
_VALID_KEY_RE = re.compile(r'^[a-z][a-z0-9_]*$')


# ═══════════════════════════════════════════════════════
# Enums
# ═══════════════════════════════════════════════════════

class Severity(IntEnum):
    RESOLVED = 0
    MINOR = 1
    MEDIUM = 2
    BLOCKING = 3


# ═══════════════════════════════════════════════════════
# Generic list parsers
# ═══════════════════════════════════════════════════════

def _parse_pipe_list(value: str) -> list[str]:
    return [s.strip() for s in value.split("|") if s.strip()]


def _parse_comma_list(value: str) -> list[str]:
    return [s.strip() for s in value.split(",") if s.strip()]


def _parse_bracket_list(value: str) -> list[str]:
    value = value.strip()
    if value in ("[]", ""):
        return []
    value = value.strip("[]")
    return [s.strip() for s in value.replace(" ", "").split(",") if s.strip()]


# ═══════════════════════════════════════════════════════
# KV file parser
# ═══════════════════════════════════════════════════════

def _is_valid_kv_key(key: str) -> bool:
    """Return True if *key* looks like a legitimate .kv field name.

    Rejects:
    - keys containing spaces, parentheses, quotes, or uppercase letters
      (e.g. ``except MemoryError``, ``print('Mode``)
    - Python keywords (e.g. ``try``, ``import``)
    """
    if not _VALID_KEY_RE.match(key):
        return False
    if keyword.iskeyword(key):
        return False
    return True


def parse_kv_file(filepath: str) -> dict[str, str]:
    """Parse a .kv file into a flat key→value dict.

    Handles:
    - ``#`` comment lines (skipped)
    - blank lines (skipped)
    - ``key: value`` pairs  (key must pass :func:`_is_valid_kv_key`)
    - continuation lines (leading whitespace → append with ``\\n``)
    - UTF-8 encoding
    """
    result: dict[str, str] = {}
    current_key: str | None = None

    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if not line or line.lstrip().startswith("#"):
                continue
            if line[0] in (" ", "\t"):
                # Continuation line
                if current_key is not None:
                    result[current_key] += "\n" + line.strip()
            else:
                idx = line.find(":")
                if idx < 1:
                    continue
                key = line[:idx].strip()
                value = line[idx + 1 :].strip()
                if not _is_valid_kv_key(key):
                    # Not a real field — reset current_key so subsequent
                    # continuation lines are not attached to it.
                    current_key = None
                    continue
                result[key] = value
                current_key = key

    return result


def parse_kb_file(path: str) -> dict[str, str]:
    """读取知识条目，自动识别 .yaml 和 .kv 格式。

    优先读 .yaml 版本（如果 PyYAML 可用），回退到 .kv 解析。
    返回扁平的 ``dict[str, str]``，与 :func:`parse_kv_file` 兼容。

    YAML 中的列表字段（match_keywords, error_signature 等）在返回时
    会被 join 成逗号分隔字符串，以保持与 KV 格式的兼容性。
    """
    # 优先读 .yaml 版本
    yaml_path = path.rsplit(".", 1)[0] + ".yaml"
    if os.path.exists(yaml_path):
        try:
            import yaml
            with open(yaml_path, encoding="utf-8") as f:
                data = yaml.safe_load(f)
            if not isinstance(data, dict):
                # YAML 文件内容不是 dict（可能为 list 或 None），回退
                return parse_kv_file(path)
            result: dict[str, str] = {}
            for k, v in data.items():
                if v is None:
                    result[k] = ""
                elif isinstance(v, str):
                    result[k] = v
                elif isinstance(v, list):
                    # 列表字段 join 成逗号分隔字符串
                    result[k] = ", ".join(str(item) for item in v)
                elif isinstance(v, bool):
                    # YAML 的 true/false → 小写字符串
                    result[k] = "true" if v else "false"
                else:
                    result[k] = str(v)
            return result
        except ImportError:
            pass  # PyYAML 不可用，回退到 KV
    # 回退到 .kv 解析
    return parse_kv_file(path)


def parse_multi_kv_file(filepath: str) -> list[dict[str, str]]:
    """Parse a .kv file containing multiple entries separated by blank lines.

    Used for principles.kv where multiple principles are in one file.
    """
    entries: list[dict[str, str]] = []
    current: dict[str, str] = {}
    current_key: str | None = None

    with open(filepath, "r", encoding="utf-8") as f:
        for raw in f:
            line = raw.rstrip("\n")
            if line.lstrip().startswith("#"):
                continue
            if not line:
                if current:
                    entries.append(current)
                    current = {}
                    current_key = None
                continue
            if line[0] in (" ", "\t"):
                if current_key is not None:
                    current[current_key] += "\n" + line.strip()
            else:
                idx = line.find(":")
                if idx < 1:
                    continue
                key = line[:idx].strip()
                value = line[idx + 1 :].strip()
                if not _is_valid_kv_key(key):
                    current_key = None
                    continue
                current[key] = value
                current_key = key

    if current:
        entries.append(current)
    return entries


# ═══════════════════════════════════════════════════════
# Data classes
# ═══════════════════════════════════════════════════════

@dataclass
class ForbidRule:
    """A forbid rule from an error entry or principle."""
    pattern: str | None = None
    reason: str | None = None
    consequence: str | None = None
    auto_reject: bool = False
    suggest: str | None = None


@dataclass
class Solution:
    """A fix recommendation or fallback."""
    priority: int = 1
    approach: str = ""
    description: str = ""
    command: str | None = None
    auto_fix: bool = False
    impl: str = ""


@dataclass
class Relations:
    causes: list[str] = field(default_factory=list)
    caused_by: list[str] = field(default_factory=list)
    similar_to: list[str] = field(default_factory=list)
    conflicts_with: list[str] = field(default_factory=list)
    prerequisite_of: list[str] = field(default_factory=list)


@dataclass
class IndexEntry:
    """One row from index.tsv."""
    id: str
    severity: Severity
    category: list[str]
    trigger_tool: list[str]
    phase: list[str]
    keywords: list[str]
    forbid_cnt: int
    auto_fix: bool
    approach: str
    principles: list[str]
    doc: str


@dataclass
class ErrorEntry:
    """Full E*.kv knowledge graph entry."""
    id: str
    trigger_tool: list[str]
    phase: list[str]
    error_signature: list[str]
    severity: Severity
    category: list[str]
    match_keywords: list[str]
    root_cause: str
    affected_scope: str
    verification_cmd: str
    rec_priority: int = 1
    rec_approach: str = ""
    rec_description: str = ""
    rec_command: str | None = None
    rec_auto_fix: bool = False
    rec_impl: str = ""
    forbid_rules: list[ForbidRule] = field(default_factory=list)
    fallback: Solution | None = None
    principles: list[str] = field(default_factory=list)
    relations: Relations = field(default_factory=Relations)
    doc_file: str = ""
    last_updated: str | None = None
    source_event: str | None = None

    # Keep raw dict for any fields we haven't mapped
    _raw: dict | None = field(default=None, repr=False)


@dataclass
class Principle:
    """One entry from principles.kv."""
    id: str
    name: str
    level: str  # critical / high / medium
    scope: list[str]
    statement: str
    forbid_rules: list[ForbidRule] = field(default_factory=list)


# ═══════════════════════════════════════════════════════
# Parsers → data classes
# ═══════════════════════════════════════════════════════

def parse_index_tsv(filepath: str) -> list[IndexEntry]:
    """Parse knowledge/graph/index.tsv into IndexEntry list.
    
    Supports both 6-column (original) and 11-column (extended) formats:
      6-col: id, severity, category, trigger_tool, phase, keywords
      11-col: id, severity, category, trigger_tool, phase, keywords,
              forbid_cnt, auto_fix, approach, principles, doc
    """
    entries: list[IndexEntry] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line or line.startswith("#"):
                continue
            cols = line.split("\t")
            if len(cols) < 6:
                continue
            try:
                severity_val = int(cols[1]) if cols[1].strip() else 1
                entries.append(IndexEntry(
                    id=cols[0],
                    severity=Severity(severity_val),
                    category=_parse_pipe_list(cols[2]),
                    trigger_tool=_parse_pipe_list(cols[3]),
                    phase=_parse_pipe_list(cols[4]),
                    keywords=_parse_comma_list(cols[5]),
                    forbid_cnt=int(cols[6]) if len(cols) > 6 and cols[6].strip() else 0,
                    auto_fix=cols[7].lower() == "true" if len(cols) > 7 else False,
                    approach=cols[8] if len(cols) > 8 else "",
                    principles=_parse_comma_list(cols[9]) if len(cols) > 9 and cols[9].strip() else [],
                    doc=cols[10] if len(cols) > 10 else "",
                ))
            except (ValueError, IndexError):
                continue
    return entries


def _parse_forbid_rules(kv_data: dict[str, str], prefix: str = "forbid") -> list[ForbidRule]:
    rules: list[ForbidRule] = []
    n = 1
    while f"{prefix}_{n}_pattern" in kv_data:
        rules.append(ForbidRule(
            pattern=kv_data.get(f"{prefix}_{n}_pattern") or None,
            reason=kv_data.get(f"{prefix}_{n}_reason") or None,
            consequence=kv_data.get(f"{prefix}_{n}_consequence") or None,
        ))
        n += 1
    return rules


def _parse_principle_forbid_rules(kv_data: dict[str, str]) -> list[ForbidRule]:
    rules: list[ForbidRule] = []
    n = 1
    while f"forbid_{n}_pattern" in kv_data:
        rules.append(ForbidRule(
            pattern=kv_data.get(f"forbid_{n}_pattern"),
            auto_reject=kv_data.get(f"forbid_{n}_auto_reject", "").lower() == "true",
            suggest=kv_data.get(f"forbid_{n}_suggest"),
        ))
        n += 1
    return rules


def parse_error_entry(filepath: str) -> ErrorEntry:
    """Parse an E*.kv file into an ErrorEntry."""
    raw = parse_kv_file(filepath)
    return ErrorEntry(
        id=raw.get("id", ""),
        trigger_tool=_parse_pipe_list(raw.get("trigger_tool", "")),
        phase=_parse_pipe_list(raw.get("phase", "")),
        error_signature=_parse_pipe_list(raw.get("error_signature", "")),
        severity=Severity(int(raw.get("severity", "1"))),
        category=_parse_pipe_list(raw.get("category", "")),
        match_keywords=_parse_comma_list(raw.get("match_keywords", "")),
        root_cause=raw.get("root_cause", ""),
        affected_scope=raw.get("affected_scope", ""),
        verification_cmd=raw.get("verification_cmd", ""),
        rec_priority=int(raw.get("rec_priority", "1")),
        rec_approach=raw.get("rec_approach", ""),
        rec_description=raw.get("rec_description", ""),
        rec_command=raw.get("rec_command") or None,
        rec_auto_fix=raw.get("rec_auto_fix", "false").lower() == "true",
        rec_impl=raw.get("rec_impl", ""),
        forbid_rules=_parse_forbid_rules(raw),
        fallback=Solution(
            priority=int(raw.get("fallback_priority", "2")),
            approach=raw.get("fallback_approach", ""),
            description=raw.get("fallback_description", ""),
            command=raw.get("fallback_command") or None,
            auto_fix=raw.get("fallback_auto_fix", "false").lower() == "true",
            impl=raw.get("fallback_impl", ""),
        ) if "fallback_approach" in raw else None,
        principles=_parse_comma_list(raw.get("principles", "")),
        relations=Relations(
            causes=_parse_bracket_list(raw.get("causes", "[]")),
            caused_by=_parse_bracket_list(raw.get("caused_by", "[]")),
            similar_to=_parse_bracket_list(raw.get("similar_to", "[]")),
            conflicts_with=_parse_bracket_list(raw.get("conflicts_with", "[]")),
            prerequisite_of=_parse_bracket_list(raw.get("prerequisite_of", "[]")),
        ),
        doc_file=raw.get("doc_file", ""),
        last_updated=raw.get("last_updated"),
        source_event=raw.get("source_event"),
        _raw=raw,
    )


def parse_principles(filepath: str) -> list[Principle]:
    """Parse principles.kv into a list of Principle."""
    raw_list = parse_multi_kv_file(filepath)
    principles: list[Principle] = []
    for raw in raw_list:
        if "id" not in raw:
            continue
        principles.append(Principle(
            id=raw.get("id", ""),
            name=raw.get("name", ""),
            level=raw.get("level", "medium"),
            scope=_parse_comma_list(raw.get("scope", "")),
            statement=raw.get("statement", ""),
            forbid_rules=_parse_principle_forbid_rules(raw),
        ))
    return principles


# ═══════════════════════════════════════════════════════
# Build context parser
# ═══════════════════════════════════════════════════════

def parse_build_context(filepath: str) -> dict[str, str]:
    """Parse a .build-context-* file (shell export format) into key→value dict."""
    result: dict[str, str] = {}
    with open(filepath, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            m = line
            if m.startswith("export "):
                m = m[7:]
            eq = m.find("=")
            if eq > 0:
                key = m[:eq].strip()
                val = m[eq + 1:].strip().strip('"').strip("'")
                result[key] = val
    return result


# ═══════════════════════════════════════════════════════
# KV writer (for index.tsv sync)
# ═══════════════════════════════════════════════════════

def write_kv_file(filepath: str, data: dict[str, str]) -> None:
    """Write a flat dict to .kv format."""
    with open(filepath, "w", encoding="utf-8") as f:
        for key, value in data.items():
            lines = value.split("\n")
            f.write(f"{key}: {lines[0]}\n")
            for cont in lines[1:]:
                f.write(f" {cont}\n")


def append_index_row(filepath: str, entry: IndexEntry) -> None:
    """Append a row to index.tsv."""
    principles_str = ",".join(entry.principles)
    row = "\t".join([
        entry.id,
        str(int(entry.severity)),
        "|".join(entry.category),
        "|".join(entry.trigger_tool),
        "|".join(entry.phase),
        ",".join(entry.keywords),
        str(entry.forbid_cnt),
        "true" if entry.auto_fix else "false",
        entry.approach,
        principles_str,
        entry.doc,
    ])
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(row + "\n")
