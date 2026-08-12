"""Knowledge graph CRUD — add / update / remove / validate.

Usage:
    python3 ohc.py graph add E081 [--non-interactive] [--field K=V ...]
    python3 ohc.py graph update E007 --field root_cause="new text"
    python3 ohc.py graph update E007 --add-relation causes=E080,E081
    python3 ohc.py graph update E007 --add-principle P-AUTOTOOLS-001
    python3 ohc.py graph update E007 --add-forbid "pattern" "reason" "consequence"
    python3 ohc.py graph update E007 --regenerate-index
    python3 ohc.py graph remove E050 [--delete] [--force]
    python3 ohc.py graph validate [--verbose] [--fix] [--coverage]
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path
from typing import Optional

from .models import parse_kv_file, parse_index_tsv, parse_principles
from .utils import graph_dir, log_info, log_ok, log_warn, log_fail

# ── Constants ──

_REQUIRED_FIELDS = [
    "id", "trigger_tool", "phase", "error_signature", "severity", "category",
    "match_keywords", "root_cause", "affected_scope", "verification_cmd",
    "rec_priority", "rec_approach", "rec_description", "rec_auto_fix",
    "rec_impl", "doc_file",
]

_VALID_RELATIONS = {"causes", "caused_by", "similar_to", "conflicts_with", "prerequisite_of"}

# Field names allowed in .kv files (from _template.kv + known extensions)
_TEMPLATE_FIELDS = {
    # Layer 0: Error Surface
    "id", "trigger_tool", "phase", "error_signature",
    # Layer 1: Recognition
    "severity", "category", "match_keywords", "title",
    # Layer 2: Diagnosis
    "root_cause", "affected_scope", "verification_cmd",
    # Layer 3: Solution (recommended)
    "rec_priority", "rec_approach", "rec_description", "rec_command",
    "rec_auto_fix", "rec_impl",
    # Layer 3: Solution (fallback)
    "fallback_priority", "fallback_approach", "fallback_description",
    "fallback_command", "fallback_auto_fix", "fallback_impl",
    # Layer 3: Solution (second fallback tier)
    "fallback_2_priority", "fallback_2_approach", "fallback_2_description",
    "fallback_2_command", "fallback_2_auto_fix", "fallback_2_impl",
    # Layer 3: Solution (third fallback tier - extreme)
    "fallback2_priority", "fallback2_approach", "fallback2_description",
    "fallback2_command", "fallback2_auto_fix", "fallback2_impl",
    # Forbid rules (dynamic N)
    "forbid_1_pattern", "forbid_1_reason", "forbid_1_consequence",
    "forbid_2_pattern", "forbid_2_reason", "forbid_2_consequence",
    # Layer 4: Principles
    "principles",
    # Relations
    "causes", "caused_by", "similar_to", "conflicts_with", "prerequisite_of",
    # Metadata
    "doc_file", "last_updated", "source_event",
    # Known extensions (used by multiple existing entries)
    "resolved_in", "resolved_note",
    # Draft-specific (allowed but stripped on merge)
    "draft", "contributor_id",
    # Knowledge collaboration (authorship & provenance)
    "authors", "source_pr", "source_commit",
    # Quality metrics (方案 D)
    "metrics_success_count", "metrics_fail_count",
    "metrics_confidence", "metrics_last_used",
}

# Regex pattern for dynamic forbid_N_xxx fields
_FORBID_FIELD_RE = re.compile(r'^forbid_\d+_(pattern|reason|consequence)$')

# ── Path helpers ──

def _gdir(pdir: str | None = None) -> Path:
    return Path(graph_dir(pdir))

def _docdir(pdir: str | None = None) -> Path:
    return Path(pdir or _gdir().parent.parent).joinpath("knowledge", "doc")

def _kv_path(eid: str, pdir: str | None = None) -> Path:
    return _gdir(pdir) / f"{eid}.kv"

def _md_path(eid: str, pdir: str | None = None) -> Path:
    return _docdir(pdir) / f"{eid}.md"

# ── ID helpers ──

def _normalize_id(raw: str) -> str:
    """Normalize and validate an entry ID like 'E081'."""
    raw = raw.strip().upper()
    m = re.match(r'^E(\d+)$', raw)
    if not m:
        log_fail(f"Invalid ID format: {raw} (expected E followed by digits)")
        return ""
    num = int(m.group(1))
    return f"E{num:03d}"

def _next_id(pdir: str | None = None) -> str:
    """Find the next available ID."""
    gdir = _gdir(pdir)
    used = set()
    for f in gdir.glob("E*.kv"):
        m = re.match(r'^E(\d+)\.kv$', f.name)
        if m:
            used.add(int(m.group(1)))
    n = 1
    while n in used:
        n += 1
    return f"E{n:03d}"

# ── KV helpers ──

def _kv_get(filepath: Path, key: str) -> str:
    data = parse_kv_file(str(filepath))
    return data.get(key, "")

def _kv_set(filepath: Path, key: str, value: str) -> None:
    """Set a key in a .kv file (replace existing or append)."""
    if not filepath.exists():
        return
    lines = filepath.read_text(encoding="utf-8").split("\n")
    replaced = False
    for i, line in enumerate(lines):
        if not line or line.lstrip().startswith("#"):
            continue
        if line[0] in (" ", "\t"):
            continue
        idx = line.find(":")
        if idx < 1:
            continue
        k = line[:idx].strip()
        if k == key:
            lines[i] = f"{key}: {value}"
            replaced = True
            break
    if not replaced:
        # Insert before doc_file line (or at end)
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("doc_file:"):
                insert_idx = i
                break
        lines.insert(insert_idx, f"{key}: {value}")
    filepath.write_text("\n".join(lines), encoding="utf-8")

def _parse_field_args(field_list: list[str] | None) -> dict[str, str]:
    """Parse --field K=V list into dict."""
    result = {}
    for f in (field_list or []):
        eq = f.find("=")
        if eq > 0:
            result[f[:eq].strip()] = f[eq + 1:].strip()
        else:
            log_warn(f"Ignoring malformed --field: {f}")
    return result

def _parse_list_value(val: str) -> list[str]:
    """Parse bracket list like [E001, E002] or comma list."""
    val = val.strip()
    if val in ("[]", ""):
        return []
    val = val.strip("[]")
    return [s.strip() for s in val.replace(" ", "").split(",") if s.strip()]

def _set_list_value(ids: list[str]) -> str:
    """Format list as [id1, id2]."""
    if not ids:
        return "[]"
    return "[" + ", ".join(ids) + "]"

# ── index.tsv sync ──

def _kv_to_tsv_row(data: dict[str, str]) -> str:
    """Extract 11 columns from .kv data for index.tsv."""
    # Count forbid entries
    forbid_cnt = 0
    for k in data:
        if re.match(r'^forbid_\d+_pattern$', k) and data[k].strip():
            forbid_cnt += 1

    # Flatten values: replace newlines with spaces for single-line TSV
    def flat(key: str, default: str = "") -> str:
        return data.get(key, default).replace("\n", " ").strip()

    # Clean principles: strip "- " prefix and inline comments
    raw_principles = flat("principles")
    cleaned = []
    for p in raw_principles.split(","):
        p = p.strip()
        if p.startswith("- "):
            p = p[2:].strip()
        if " #" in p:
            p = p[:p.index(" #")].strip()
        if p:
            cleaned.append(p)
    principles_str = ", ".join(cleaned)

    return "\t".join([
        flat("id"),
        flat("severity", "1"),
        flat("category"),
        flat("trigger_tool"),
        flat("phase"),
        flat("match_keywords"),
        str(forbid_cnt),
        flat("rec_auto_fix", "false"),
        flat("rec_approach"),
        principles_str,
        flat("doc_file"),
    ])

def _sync_index(eid: str, pdir: str | None = None) -> None:
    """Update or append a row in index.tsv from .kv data."""
    gdir = _gdir(pdir)
    index_path = gdir / "index.tsv"
    kv_path = _kv_path(eid, pdir)
    if not kv_path.exists():
        return

    data = parse_kv_file(str(kv_path))
    new_row = _kv_to_tsv_row(data)

    if not index_path.exists():
        index_path.write_text(new_row + "\n", encoding="utf-8")
        return

    lines = index_path.read_text(encoding="utf-8").split("\n")
    found = False
    for i, line in enumerate(lines):
        if line.startswith("#") or not line.strip():
            continue
        cols = line.split("\t")
        if cols and cols[0] == eid:
            lines[i] = new_row
            found = True
            break
    if not found:
        # Append after last data line
        insert_idx = len(lines)
        for i in range(len(lines) - 1, -1, -1):
            if lines[i].strip() and not lines[i].startswith("#"):
                insert_idx = i + 1
                break
        lines.insert(insert_idx, new_row)

    index_path.write_text("\n".join(lines), encoding="utf-8")

# ═══════════════════════════════════════════════════════
# cmd: add
# ═══════════════════════════════════════════════════════

def cmd_add(
    id_str: str | None = None,
    *,
    non_interactive: bool = False,
    fields: list[str] | None = None,
    pdir: str | None = None,
    draft: bool = False,
) -> int:
    from .utils import get_agent_id

    gdir = _gdir(pdir)
    docdir = _docdir(pdir)

    # ── Draft mode setup ──
    if draft:
        agent_id = get_agent_id(pdir)

    # ID
    if not id_str:
        nid = _next_id(pdir)
        print(f"📝 下一个可用 ID: {nid}")
        print(f"   用法: python3 ohc.py graph add {nid} --field ...")
        return 0

    eid = _normalize_id(id_str)
    if not eid:
        return 1

    if draft:
        # In draft mode, write to draft/ directory
        draft_dir = _gdir(pdir).parent / "drafts"
        draft_dir.mkdir(exist_ok=True)
        kv_path = draft_dir / f"{eid}-draft-{agent_id}.kv"
        md_path = draft_dir / f"{eid}-draft-{agent_id}.md"
    else:
        kv_path = _kv_path(eid, pdir)
        md_path = _md_path(eid, pdir)

    # Check not exists
    if kv_path.exists():
        log_fail(f"{kv_path.name} already exists")
        return 1

    # Template
    template = gdir / "_template.kv"
    if not template.exists():
        log_fail("_template.kv not found")
        return 1

    today = date.today().isoformat()
    content = template.read_text(encoding="utf-8")
    content = content.replace("Ennn", eid).replace("E{NNN}", eid)
    content = re.sub(r'last_updated:.*', f'last_updated: {today}', content)

    # In draft mode, tag the contributor
    if draft:
        content += f"\ndraft: true\ncontributor_id: {agent_id}\n"

    kv_path.write_text(content, encoding="utf-8")
    log_ok(f"Created {kv_path}")

    # Doc skeleton
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_skeleton = f"""# {eid} — [简短错误描述]

## 错误特征
[描述触发此错误模式的典型日志输出或症状]

## 触发条件
- 构建系统: [autotools/cmake/meson/...]
- 阶段: [configure/make/install/...]

## 根因分析
[详细解释错误的根本原因]

## 解决方案

### 推荐方案
[描述修复步骤]

### 禁止做法
- ❌ [描述不应采取的操作]

## 验证
```bash
[验证修复的命令]
```

## 关联条目
- 相关: [E???]
"""
    md_path.write_text(md_skeleton, encoding="utf-8")
    log_ok(f"Created {md_path}")

    # Apply --field values
    field_dict = _parse_field_args(fields)
    for k, v in field_dict.items():
        _kv_set(kv_path, k, v)

    # Interactive edit (skip in draft mode)
    if not draft and not non_interactive and sys.stdin.isatty():
        editor = os.environ.get("EDITOR", "vi")
        log_info(f"Press Enter to edit {eid}.kv with {editor} (or 's' to skip)...")
        try:
            choice = input().strip().lower()
        except EOFError:
            choice = "s"
        if choice != "s":
            os.system(f"{editor} {kv_path}")

    # Validate required fields
    data = parse_kv_file(str(kv_path))
    missing = [f for f in _REQUIRED_FIELDS if f not in data or not data[f].strip()]
    if missing:
        log_warn(f"Missing required fields: {missing}")
        if not draft and not non_interactive and sys.stdin.isatty():
            try:
                choice = input("Continue adding to index? (y/n): ").strip().lower()
            except EOFError:
                choice = "n"
            if choice != "y":
                log_info("Cancelled. Files created but not indexed.")
                return 0

    # Validate principles references (non-draft only)
    if not draft:
        princs = [s.strip() for s in data.get("principles", "").split(",") if s.strip()]
        if princs:
            p_file = gdir / "principles.kv"
            if p_file.exists():
                known_principles = set()
                for p in parse_principles(str(p_file)):
                    known_principles.add(p.id)
                unknown_princs = [p for p in princs if p not in known_principles]
                if unknown_princs:
                    log_fail(f"Unknown principle(s): {unknown_princs} "
                             f"(valid: {sorted(known_principles)})")
                    log_info("Available principles: " + ", ".join(sorted(known_principles)))
                    return 1

    # In draft mode: do NOT write to index.tsv, do NOT validate
    if draft:
        # Check if key fields were provided via --field
        data = parse_kv_file(str(kv_path))
        has_content = (
            data.get("root_cause", "").strip() and
            len(data.get("root_cause", "").strip()) > 20 and
            data.get("error_signature", "").strip() and
            "configure|cmake|meson" not in data.get("error_signature", "")
        )

        if has_content:
            log_ok(f"Draft {eid} created with content (contributor: {agent_id}) — not indexed")
            print(f"\n  ✅ 草稿已包含实质性内容（root_cause + error_signature 已填写）")
            print(f"  📄 KV: {kv_path}")
            print(f"  📄 MD: {md_path}")
            print(f"  下一步: 继续编译流程或在 finish 前补充更多字段\n")
            return 0
        else:
            log_ok(f"Draft {eid} created (contributor: {agent_id}) — EMPTY TEMPLATE")

            # Emit HANDOFF block — this is a STRONG signal
            print()
            print("╔═══ ⚠️  DRAFT KNOWLEDGE HANDOFF — AI ACTION REQUIRED ═╗")
            print(f"║ DRAFT_ID: {eid}")
            print(f"║ KV_FILE: {kv_path}")
            print(f"║ MD_FILE: {md_path}")
            print(f"║ CONTRIBUTOR: {agent_id}")
            print("║ STATUS: ❌ template EMPTY — must fill content before finish")
            print("║")
            print("║ ❗ finish 管线会拒绝空草稿！必须先填写内容！")
            print("║")
            print("║ 方式 A（推荐）: 直接写入文件")
            print(f"║   使用 filemgr-editFile 编辑 {kv_path}")
            print("║   必填字段:")
            print("║     - error_signature: 典型错误日志正则（| 分隔）")
            print("║     - root_cause: 根因分析（为什么会出现这个错误）")
            print("║     - match_keywords: 检索关键词（逗号分隔）")
            print("║     - rec_description: 推荐解决方案描述")
            print("║     - rec_command: 一行修复命令")
            print("║     - affected_scope: 受影响的软件范围")
            print("║     - verification_cmd: 验证修复的命令")
            print("║     - category: 分类标签")
            print("║")
            print("║ 方式 B: 重新创建时带 --field 参数")
            print("║   python3 ohc-run.py graph add E090 --draft \\")
            print("║     --field 'root_cause=实际根因' \\")
            print("║     --field 'error_signature=实际正则' \\")
            print("║     --field 'match_keywords=关键词列表'")
            print("║")
            print(f"║ MD 文件也需填写: {md_path}")
            print("║")
            print("║ ⚠️  不填写内容，finish 将失败！草稿会被主编审核拒绝！")
            print("╚═════════════════════════════════════════════════════╝")
            print()
            # Return exit code 2 to signal "needs AI intervention"
            return 2

    # Append to index.tsv
    _sync_index(eid, pdir)
    log_ok(f"Added {eid} to index.tsv")

    # Update last_updated
    _kv_set(kv_path, "last_updated", today)

    # Final validate
    cmd_validate(pdir=pdir)
    return 0

# ═══════════════════════════════════════════════════════
# cmd: update
# ═══════════════════════════════════════════════════════

def cmd_update(
    id_str: str,
    *,
    fields: list[str] | None = None,
    regenerate_index: bool = False,
    add_relation: str | None = None,
    add_principle: str | None = None,
    add_forbid: list[str] | None = None,
    no_validate: bool = False,
    pdir: str | None = None,
) -> int:
    eid = _normalize_id(id_str)
    if not eid:
        return 1

    kv_path = _kv_path(eid, pdir)
    if not kv_path.exists():
        log_fail(f"{eid}.kv not found")
        return 1

    gdir = _gdir(pdir)
    today = date.today().isoformat()
    changed = False

    # --field
    field_dict = _parse_field_args(fields)
    for k, v in field_dict.items():
        _kv_set(kv_path, k, v)
        changed = True
    if field_dict:
        log_ok(f"Updated fields: {list(field_dict.keys())}")

    # --add-relation TYPE=IDS
    if add_relation:
        eq = add_relation.find("=")
        if eq < 1:
            log_fail("--add-relation format: TYPE=IDS (e.g. causes=E080,E081)")
            return 1
        rel_type = add_relation[:eq].strip()
        rel_ids = [s.strip() for s in add_relation[eq + 1:].split(",") if s.strip()]
        if rel_type not in _VALID_RELATIONS:
            log_fail(f"Invalid relation type: {rel_type} (valid: {', '.join(sorted(_VALID_RELATIONS))})")
            return 1
        current = _parse_list_value(_kv_get(kv_path, rel_type))
        merged = sorted(set(current + rel_ids))
        _kv_set(kv_path, rel_type, _set_list_value(merged))
        log_ok(f"Updated {rel_type}: {_set_list_value(merged)}")
        changed = True

    # --add-principle P-XXX
    if add_principle:
        p_file = gdir / "principles.kv"
        known = set()
        if p_file.exists():
            for p in parse_principles(str(p_file)):
                known.add(p.id)
        if add_principle not in known:
            log_fail(f"Principle {add_principle} not found in principles.kv")
            log_info(f"Available: {', '.join(sorted(known))}")
            return 1
        current = [s.strip() for s in _kv_get(kv_path, "principles").split(",") if s.strip()]
        if add_principle not in current:
            current.append(add_principle)
            _kv_set(kv_path, "principles", ", ".join(current))
            log_ok(f"Added principle: {add_principle}")
        changed = True

    # --add-forbid PAT REASON CONSEQ
    if add_forbid and len(add_forbid) == 3:
        # Find next available forbid_N
        data = parse_kv_file(str(kv_path))
        n = 1
        while f"forbid_{n}_pattern" in data:
            n += 1
        # Insert before doc_file
        lines = kv_path.read_text(encoding="utf-8").split("\n")
        insert_idx = len(lines)
        for i, line in enumerate(lines):
            if line.startswith("doc_file:"):
                insert_idx = i
                break
        new_lines = [
            f"forbid_{n}_pattern: {add_forbid[0]}",
            f"forbid_{n}_reason: {add_forbid[1]}",
            f"forbid_{n}_consequence: {add_forbid[2]}",
        ]
        for j, nl in enumerate(new_lines):
            lines.insert(insert_idx + j, nl)
        kv_path.write_text("\n".join(lines), encoding="utf-8")
        log_ok(f"Added forbid_{n}")
        changed = True

    # Update last_updated
    if changed:
        _kv_set(kv_path, "last_updated", today)

    # Sync index
    if regenerate_index or changed:
        _sync_index(eid, pdir)

    # Validate
    if not no_validate:
        cmd_validate(pdir=pdir)

    return 0

# ═══════════════════════════════════════════════════════
# cmd: remove
# ═══════════════════════════════════════════════════════

def cmd_remove(
    id_str: str,
    *,
    delete: bool = False,
    force: bool = False,
    pdir: str | None = None,
) -> int:
    eid = _normalize_id(id_str)
    if not eid:
        return 1

    kv_path = _kv_path(eid, pdir)
    md_path = _md_path(eid, pdir)

    if not kv_path.exists():
        log_fail(f"{eid}.kv not found")
        return 1

    gdir = _gdir(pdir)

    # Scan external references
    refs: dict[str, list[str]] = {}
    for other in gdir.glob("E*.kv"):
        if other.name == f"{eid}.kv":
            continue
        data = parse_kv_file(str(other))
        for rel_type in _VALID_RELATIONS:
            ids = _parse_list_value(data.get(rel_type, ""))
            if eid in ids:
                refs.setdefault(other.stem, []).append(rel_type)

    if refs:
        log_warn(f"External references found:")
        for other_id, rel_types in refs.items():
            log_warn(f"  {other_id}: {', '.join(rel_types)}")
        if not force:
            try:
                choice = input("Continue? (y/n): ").strip().lower()
            except EOFError:
                choice = "n"
            if choice != "y":
                log_info("Cancelled.")
                return 0

    if delete:
        if not force:
            try:
                choice = input(f"Permanently DELETE {eid}? Type 'yes': ").strip()
            except EOFError:
                choice = ""
            if choice != "yes":
                log_info("Cancelled.")
                return 0

        kv_path.unlink(missing_ok=True)
        md_path.unlink(missing_ok=True)
        log_ok(f"Deleted {eid}.kv and {eid}.md")

        # Remove from index.tsv
        index_path = gdir / "index.tsv"
        if index_path.exists():
            lines = index_path.read_text(encoding="utf-8").split("\n")
            lines = [l for l in lines if not l.startswith(eid + "\t")]
            index_path.write_text("\n".join(lines), encoding="utf-8")
            log_ok(f"Removed {eid} from index.tsv")

        if refs:
            log_info("Clean up references with:")
            for other_id, rel_types in refs.items():
                for rt in rel_types:
                    print(f"  python3 ohc.py graph update {other_id} --field '{rt}='")
    else:
        # Archive mode
        if kv_path.exists():
            archived_kv = kv_path.with_suffix(".kv.archived")
            kv_path.rename(archived_kv)
            log_ok(f"Archived → {archived_kv.name}")
        if md_path.exists():
            archived_md = md_path.with_suffix(".md.archived")
            md_path.rename(archived_md)
            log_ok(f"Archived → {archived_md.name}")

        # Comment out in index.tsv
        index_path = gdir / "index.tsv"
        if index_path.exists():
            lines = index_path.read_text(encoding="utf-8").split("\n")
            for i, line in enumerate(lines):
                if line.startswith(eid + "\t"):
                    lines[i] = f"# ARCHIVED: {line}"
                    break
            index_path.write_text("\n".join(lines), encoding="utf-8")
            log_ok(f"Archived {eid} in index.tsv")

        print(f"\n  ↩️  To restore:")
        print(f"    mv {kv_path.with_suffix('.kv.archived')} {kv_path}")
        if md_path.exists():
            print(f"    mv {md_path.with_suffix('.md.archived')} {md_path}")
        print(f"    Edit index.tsv: uncomment {eid} row")

    return 0

# ═══════════════════════════════════════════════════════
# cmd: validate
# ═══════════════════════════════════════════════════════

def cmd_validate(
    *,
    verbose: bool = False,
    fix: bool = False,
    coverage: bool = False,
    pdir: str | None = None,
) -> int:
    gdir = _gdir(pdir)
    docdir = _docdir(pdir)
    index_path = gdir / "index.tsv"
    principles_path = gdir / "principles.kv"

    errors = 0
    warnings = 0

    # Collect data
    kv_files = sorted(gdir.glob("E[0-9]*.kv"))
    kv_files = [f for f in kv_files if re.match(r'^E\d+\.kv$', f.name)]
    md_files = sorted(docdir.glob("E[0-9]*.md")) if docdir.exists() else []
    md_files = [f for f in md_files if re.match(r'^E\d+\.md$', f.name)]
    kv_ids = {f.stem for f in kv_files}
    md_ids = {f.stem for f in md_files}
    index_entries = parse_index_tsv(str(index_path)) if index_path.exists() else []

    print("🔍 Knowledge Graph Validation")
    print(f"   .kv files: {len(kv_files)}, .md files: {len(md_files)}, index rows: {len(index_entries)}")
    print()

    # Check 1: .kv ↔ .md correspondence
    only_kv = kv_ids - md_ids
    only_md = md_ids - kv_ids
    for k in sorted(only_kv):
        log_fail(f"[C1] {k}.kv exists but {k}.md missing")
        errors += 1
        if fix:
            # Auto-create missing .md skeleton
            md_skeleton = f"""# {k} — [简短错误描述]

## 错误特征
[待补充]

## 根因分析
[待补充]

## 解决方案
[待补充]

## 验证
```bash
[待补充]
```
"""
            skeleton_path = docdir / f"{k}.md"
            skeleton_path.parent.mkdir(parents=True, exist_ok=True)
            skeleton_path.write_text(md_skeleton, encoding="utf-8")
            log_info(f"[C1] Auto-created {skeleton_path}")
            md_ids.add(k)
    for m in sorted(only_md):
        log_fail(f"[C1] {m}.md exists but {m}.kv missing")
        errors += 1
    if not only_kv and not only_md:
        if verbose:
            log_ok(f"[C1] .kv ↔ .md correspondence: OK ({len(kv_ids)} pairs)")

    # Check 2: index.tsv row count
    if len(index_entries) != len(kv_files):
        log_fail(f"[C2] index.tsv={len(index_entries)} rows vs .kv={len(kv_files)} files")
        errors += 1
        if fix:
            _regenerate_index(kv_files, index_path)
            log_info("[C2] index.tsv regenerated")
    else:
        if verbose:
            log_ok(f"[C2] index.tsv row count: OK")

    # Check 3: no duplicate IDs
    seen = set()
    for entry in index_entries:
        if entry.id in seen:
            log_fail(f"[C3] Duplicate ID: {entry.id}")
            errors += 1
        seen.add(entry.id)
    if verbose and len(seen) == len(index_entries):
        log_ok("[C3] No duplicate IDs")

    # Check 4: required fields
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        missing = [f for f in _REQUIRED_FIELDS if f not in data or not data[f].strip()]
        if missing:
            log_fail(f"[C4] {kvf.stem}: missing fields: {missing}")
            errors += 1
    if verbose:
        log_ok(f"[C4] Required fields checked")

    # Check 4.5: non-standard field names
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        unknown = set()
        for key in data:
            if key in _TEMPLATE_FIELDS or _FORBID_FIELD_RE.match(key):
                continue
            unknown.add(key)
        if unknown:
            log_fail(f"[C4.5] {kvf.stem}: non-standard fields: {sorted(unknown)}")
            errors += 1
            if fix:
                # Auto-fix: rename 'doc' → 'doc_file'
                if "doc" in unknown and "doc_file" not in data:
                    lines = kvf.read_text(encoding="utf-8").split("\n")
                    for i, line in enumerate(lines):
                        if line.startswith("doc:") and not line.startswith("doc_file:"):
                            lines[i] = "doc" + line[3:].replace("doc:", "doc_file:", 1)
                            lines[i] = f"doc_file:{line[4:]}"
                            break
                    kvf.write_text("\n".join(lines), encoding="utf-8")
                    log_info(f"[C4.5] {kvf.stem}: auto-renamed 'doc' → 'doc_file'")

    # Check 4.6: 'doc' field alias (should be 'doc_file')
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        if "doc" in data and "doc_file" not in data:
            log_fail(f"[C4.6] {kvf.stem}: uses 'doc' instead of standard 'doc_file'")
            errors += 1
            if fix:
                _kv_set(kvf, "doc_file", data["doc"])
                # Remove old 'doc' line
                lines = kvf.read_text(encoding="utf-8").split("\n")
                new_lines = [l for l in lines if not l.startswith("doc:") or l.startswith("doc_file:")]
                kvf.write_text("\n".join(new_lines), encoding="utf-8")
                log_info(f"[C4.6] {kvf.stem}: auto-fixed 'doc' → 'doc_file'")

    # Check 5: principles references
    known_principles = set()
    if principles_path.exists():
        for p in parse_principles(str(principles_path)):
            known_principles.add(p.id)
    for kvf in kv_files:
        princs_raw = _kv_get(kvf, "principles")
        # Strip inline comments (e.g., "- P-XXX  # reason")
        princs = []
        for s in princs_raw.split(","):
            s = s.strip()
            # Remove "- " prefix if present
            if s.startswith("- "):
                s = s[2:].strip()
            # Remove inline comments
            if " #" in s:
                s = s[:s.index(" #")].strip()
            if s:
                princs.append(s)
        for p in princs:
            if p not in known_principles and known_principles:
                log_fail(f"[C5] {kvf.stem}: unknown principle {p}")
                errors += 1
    if verbose:
        log_ok("[C5] Principles references checked")

    # Check 6: relation ID references
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        for rel_type in _VALID_RELATIONS:
            ids = _parse_list_value(data.get(rel_type, ""))
            for rid in ids:
                if rid not in kv_ids:
                    log_fail(f"[C6] {kvf.stem}.{rel_type}: references non-existent {rid}")
                    errors += 1
    if verbose:
        log_ok("[C6] Relation references checked")

    # Check 7: severity validity
    for kvf in kv_files:
        sev = _kv_get(kvf, "severity").strip()
        if sev not in ("1", "2", "3"):
            log_fail(f"[C7] {kvf.stem}: invalid severity '{sev}'")
            errors += 1
    if verbose:
        log_ok("[C7] Severity values checked")

    # Check 8: index.tsv ↔ .kv content consistency
    for entry in index_entries:
        kvf = gdir / f"{entry.id}.kv"
        if not kvf.exists():
            continue
        data = parse_kv_file(str(kvf))
        if data.get("severity", "") != str(entry.severity):
            log_warn(f"[C8] {entry.id}: severity mismatch (tsv={entry.severity} kv={data.get('severity')})")
            warnings += 1
        if entry.approach and data.get("rec_approach", "") != entry.approach:
            log_warn(f"[C8] {entry.id}: approach mismatch")
            warnings += 1
    if verbose:
        log_ok("[C8] Content consistency checked")

    # Check 9: coverage
    forbid_filled = 0
    fallback_filled = 0
    principles_filled = 0
    autofix_true = 0
    autofix_false = 0
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        if any(v.strip() for k, v in data.items() if re.match(r'^forbid_\d+_pattern$', k)):
            forbid_filled += 1
        if data.get("fallback_approach", "").strip():
            fallback_filled += 1
        if data.get("principles", "").strip():
            principles_filled += 1
        af = data.get("rec_auto_fix", "false").strip().lower()
        if af == "true":
            autofix_true += 1
        elif af == "false":
            autofix_false += 1
    n = len(kv_files) or 1
    print()
    print(f"  📊 Coverage Report ({len(kv_files)} entries):")
    print(f"     forbid_* filled:    {forbid_filled}/{n} ({forbid_filled * 100 // n}%)")
    print(f"     fallback filled:    {fallback_filled}/{n} ({fallback_filled * 100 // n}%)")
    print(f"     principles filled:  {principles_filled}/{n} ({principles_filled * 100 // n}%)")
    print(f"     auto_fix=true:      {autofix_true}, auto_fix=false: {autofix_false}")

    print()

    # Check 10: template placeholder residue
    _TEMPLATE_PLACEHOLDERS = {
        "keyword1", "keyword2", "keyword3",
        "category-name", "approach-identifier",
    }
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        # Check match_keywords for template default
        mk = data.get("match_keywords", "").strip()
        if mk.lower() == "keyword1, keyword2, keyword3":
            log_fail(f"[C10] {kvf.stem}.match_keywords: unchanged template default keywords")
            errors += 1
        # Check category for template placeholder
        cat = data.get("category", "").strip()
        if cat.lower() == "category-name":
            log_fail(f"[C10] {kvf.stem}.category: unchanged template placeholder")
            errors += 1
    if verbose:
        log_ok("[C10] Template placeholder check")

    # Check 11: rec_auto_fix must be exactly true or false (no pipe values)
    for kvf in kv_files:
        af_raw = _kv_get(kvf, "rec_auto_fix")
        af = af_raw.strip()
        # Strip inline comments
        if " #" in af:
            af = af[:af.index(" #")].strip()
        if "|" in af:
            log_fail(f"[C11] {kvf.stem}.rec_auto_fix: invalid pipe-separated value '{af}' (must be 'true' or 'false')")
            errors += 1
        elif af not in ("true", "false"):
            log_fail(f"[C11] {kvf.stem}.rec_auto_fix: must be 'true' or 'false', got '{af}'")
            errors += 1
    if verbose:
        log_ok("[C11] rec_auto_fix format checked")

    # Check 12: draft leakage detection
    # No .kv file in knowledge/graph/ should contain draft:true
    for kvf in kv_files:
        data = parse_kv_file(str(kvf))
        if data.get("draft", "").strip().lower() == "true":
            log_fail(f"[C12] {kvf.stem}: contains 'draft: true' — draft file leaked into formal graph directory")
            errors += 1
        if data.get("contributor_id", "").strip():
            log_fail(f"[C12] {kvf.stem}: contains 'contributor_id' — draft field leaked into formal graph directory")
            errors += 1
    # Also check that knowledge/graph/draft/ directory does not exist
    draft_subdir = gdir / "draft"
    if draft_subdir.is_dir():
        leaked = list(draft_subdir.glob("*.kv"))
        if leaked:
            log_fail(f"[C12] knowledge/graph/draft/ directory exists with {len(leaked)} .kv files — use knowledge/drafts/ instead")
            errors += 1
    if verbose:
        log_ok("[C12] Draft leakage check")

    if errors:
        log_fail(f"❌ {errors} errors, {warnings} warnings")
    else:
        log_ok(f"✅ All checks passed ({warnings} warnings)")

    return 1 if errors else 0


def _regenerate_index(kv_files: list[Path], index_path: Path) -> None:
    """Regenerate index.tsv from all .kv files, preserving comments."""
    # Preserve comment lines
    comment_lines = []
    if index_path.exists():
        for line in index_path.read_text(encoding="utf-8").split("\n"):
            if line.startswith("#") or not line.strip():
                comment_lines.append(line)

    rows = []
    for kvf in sorted(kv_files):
        try:
            data = parse_kv_file(str(kvf))
            rows.append(_kv_to_tsv_row(data))
        except Exception:
            # Skip files that can't be parsed
            continue

    content = "\n".join(comment_lines + rows) + "\n"
    index_path.write_text(content, encoding="utf-8")


def _get_git_author() -> str:
    """Get current git user name."""
    import subprocess
    try:
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


# ═══════════════════════════════════════════════════════
# cmd: promote (draft → official)
# ═══════════════════════════════════════════════════════

def cmd_promote(
    draft_id: str,
    *,
    target_id: str | None = None,
    force: bool = False,
    no_merge: bool = False,
    pdir: str | None = None,
) -> int:
    """Promote a draft to official knowledge graph entry.

    1. Quality gate: error_signature/root_cause/rec_approach must be non-empty (--force to bypass)
    2. Merge detection: scan all drafts for similar ones (keyword overlap >50%)
    3. Contributors: first author from draft, merged drafts append as 2nd/3rd
    4. Strips draft-specific fields, assigns E-number
    5. Writes E###.kv + doc/E###.md, regenerates index.tsv
    6. Removes promoted draft(s)
    """
    project = Path(pdir) if pdir else Path(find_project_dir())
    graph_dir = project / "knowledge" / "graph"
    drafts_dir = project / "knowledge" / "drafts"
    doc_dir = project / "knowledge" / "doc"

    if not draft_id.startswith("DRAFT"):
        draft_id = f"DRAFT-{draft_id}"
    draft_path = drafts_dir / f"{draft_id}.kv"
    if not draft_path.exists():
        log_fail(f"草稿不存在: {draft_path}")
        return 1

    # ── Parse draft fields ──
    def _parse_fields(text):
        fields = {}
        for line in text.split('\n'):
            line = line.strip()
            if not line or line.startswith('#'): continue
            m = re.match(r'^(\w+):\s*(.*)', line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()
        return fields

    content = draft_path.read_text(encoding="utf-8")
    fields = _parse_fields(content)

    # ── Quality gate ──
    quality_fields = ['error_signature', 'root_cause', 'rec_approach']
    missing_quality = [f for f in quality_fields if not fields.get(f, '').strip()]
    if missing_quality and not force:
        log_fail(f"❌ 质量门禁未通过: 以下字段为空: {missing_quality}")
        log_info("   补充后重试，或使用 --force 跳过质量检查")
        return 1
    elif missing_quality and force:
        log_warn(f"⚠️ 质量门禁跳过 (--force): 空字段 {missing_quality}")

    # ── Merge detection ──
    merged_drafts = []
    merged_contributors = []
    if not no_merge:
        target_kws = set(k.strip() for k in fields.get('match_keywords', '').split(',') if k.strip())
        for other in sorted(drafts_dir.glob("DRAFT-*.kv")):
            if other.name == draft_path.name:
                continue
            other_fields = _parse_fields(other.read_text(encoding='utf-8'))
            other_kws = set(k.strip() for k in other_fields.get('match_keywords', '').split(',') if k.strip())
            if target_kws and other_kws:
                overlap = len(target_kws & other_kws) / max(len(target_kws), 1)
                if overlap > 0.5:
                    merged_drafts.append((other, other_fields, overlap))
                    other_contrib = other_fields.get('contributor_id', other_fields.get('authors', ''))
                    if other_contrib and other_contrib not in merged_contributors:
                        merged_contributors.append(other_contrib)
                    log_info(f"  🔀 发现相似草稿: {other.stem} (关键词重合 {overlap:.0%})")

    # Merge fields from similar drafts (fill empty fields only)
    for other_path, other_fields, _ in merged_drafts:
        for k, v in other_fields.items():
            if k in ('id', 'draft', 'contributor_id', 'authors'):
                continue
            if not fields.get(k, '').strip() and v.strip():
                fields[k] = v
                log_info(f"    合并字段 {k} ← {other_path.stem}")

    # ── Contributors ──
    primary_contrib = fields.get('contributor_id', fields.get('authors', _get_git_author()))
    all_contributors = [primary_contrib] + merged_contributors
    # Deduplicate
    seen = set()
    unique_contributors = []
    for c in all_contributors:
        if c and c not in seen:
            seen.add(c)
            unique_contributors.append(c)

    # ── Strip draft-specific fields ──
    for field in ("draft", "contributor_id"):
        content = re.sub(rf'^{field}:.*$\n?', '', content, flags=re.MULTILINE)

    # ── Assign E-number ──
    if not target_id:
        existing = {f.stem for f in graph_dir.iterdir()
                    if f.name.startswith("E") and f.suffix == ".kv" and f.name != "_template.kv"}
        n = 1
        while f"E{n:03d}" in existing:
            n += 1
        target_id = f"E{n:03d}"

    # ── Fill defaults ──
    defaults = {'id': target_id, 'severity': '2', 'rec_auto_fix': 'false',
                'rec_impl': 'manual', 'rec_priority': '1',
                'last_updated': str(date.today()),
                'authors': ', '.join(unique_contributors[:3])}
    additions = [f'{k}:               {v}' for k, v in defaults.items()
                 if k not in fields or not fields.get(k)]
    if additions:
        content = content.rstrip('\n') + '\n' + '\n'.join(additions) + '\n'
    content = re.sub(r'^id:.*$', f'id:                     {target_id}', content, flags=re.MULTILINE)

    # ── Write KV ──
    kv_path = graph_dir / f"{target_id}.kv"
    kv_path.write_text(content, encoding="utf-8")
    log_ok(f"✅ 正式条目: {kv_path.relative_to(project)}")

    # ── Write doc ──
    doc_dir.mkdir(parents=True, exist_ok=True)
    app = fields.get('rec_approach', fields.get('root_cause', ''))[:60]
    doc_path = doc_dir / f"{target_id}.md"
    contrib_line = ', '.join(unique_contributors[:3]) if unique_contributors else 'unknown'
    doc_path.write_text(
        f"# {target_id}: {app or '未命名错误模式'}\n\n"
        f"## 基本信息\n- **严重度**: {fields.get('severity', '2')}\n"
        f"- **类别**: {fields.get('category', '')}\n\n"
        f"## 错误特征\n```\n{fields.get('error_signature', '(待补充)')}\n```\n\n"
        f"## 根因分析\n{fields.get('root_cause', '(待补充)')}\n\n"
        f"## 来源\n- 草稿: {draft_id}\n- 合并: {', '.join(d.stem for _, _, d in [(d[0], d[1], d[0]) for d in merged_drafts]) or '无'}\n"
        f"- 贡献者: {contrib_line}\n- 提升日期: {date.today()}\n",
        encoding="utf-8")
    log_ok(f"✅ 配套文档: {doc_path.relative_to(project)}")

    # ── Regenerate index ──
    kv_files = sorted(graph_dir.glob("E[0-9]*.kv"))
    kv_files = [f for f in kv_files if re.match(r'^E\d+\.kv$', f.name)]
    _regenerate_index(kv_files, graph_dir / "index.tsv")
    log_ok(f"✅ index.tsv 已更新")

    # ── Remove drafts ──
    draft_path.unlink()
    for other_path, _, _ in merged_drafts:
        other_path.unlink()
        log_info(f"  🗑️ 已移除合并草稿: {other_path.stem}")

    log_info(f"🎉 {draft_id} → {target_id} 提升完成"
             f"{' (合并 ' + str(len(merged_drafts)) + ' 草稿)' if merged_drafts else ''}")
    if unique_contributors:
        log_info(f"   贡献者: {', '.join(unique_contributors[:3])}")
    return 0


# ═══════════════════════════════════════════════════════
# CLI entry
# ═══════════════════════════════════════════════════════

def graph_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc graph", description="Knowledge graph management")
    sub = parser.add_subparsers(dest="graph_command")

    # add
    p_add = sub.add_parser("add", help="Create new entry")
    p_add.add_argument("id", nargs="?", help="Entry ID (e.g. E081)")
    p_add.add_argument("-n", "--non-interactive", action="store_true")
    p_add.add_argument("--field", action="append", metavar="K=V")
    p_add.add_argument("--project-dir")
    p_add.add_argument("--draft", action="store_true",
                       help="Write to draft/ directory (not indexed, not validated)")

    # update
    p_upd = sub.add_parser("update", help="Update existing entry")
    p_upd.add_argument("id", help="Entry ID")
    p_upd.add_argument("--field", action="append", metavar="K=V")
    p_upd.add_argument("--regenerate-index", action="store_true")
    p_upd.add_argument("--add-relation", metavar="TYPE=IDS")
    p_upd.add_argument("--add-principle", metavar="P-XXX")
    p_upd.add_argument("--add-forbid", nargs=3, metavar=("PAT", "REASON", "CONSEQ"))
    p_upd.add_argument("--no-validate", action="store_true")
    p_upd.add_argument("--project-dir")

    # remove
    p_rm = sub.add_parser("remove", help="Archive/delete entry")
    p_rm.add_argument("id", help="Entry ID")
    p_rm.add_argument("--delete", "-d", action="store_true")
    p_rm.add_argument("--force", "-f", action="store_true")
    p_rm.add_argument("--project-dir")

    # validate
    p_val = sub.add_parser("validate", help="Consistency check")
    p_val.add_argument("--verbose", "-v", action="store_true")
    p_val.add_argument("--fix", action="store_true")
    p_val.add_argument("--coverage", "-c", action="store_true")
    p_val.add_argument("--project-dir")

    # promote
    p_promo = sub.add_parser("promote", help="Promote draft to official entry")
    p_promo.add_argument("draft_id", help="Draft ID (e.g. DRAFT-001 or 001)")
    p_promo.add_argument("--target-id", help="Target E-number (auto-assigned if omitted)")
    p_promo.add_argument("--force", action="store_true", help="Skip quality gate")
    p_promo.add_argument("--no-merge", action="store_true", help="Skip merge detection")
    p_promo.add_argument("--project-dir")

    args = parser.parse_args(argv)

    if args.graph_command == "add":
        return cmd_add(
            args.id,
            non_interactive=args.non_interactive,
            fields=args.field,
            pdir=getattr(args, 'project_dir', None),
            draft=getattr(args, 'draft', False),
        )
    elif args.graph_command == "update":
        return cmd_update(
            args.id,
            fields=args.field,
            regenerate_index=args.regenerate_index,
            add_relation=args.add_relation,
            add_principle=args.add_principle,
            add_forbid=args.add_forbid,
            no_validate=args.no_validate,
            pdir=getattr(args, 'project_dir', None),
        )
    elif args.graph_command == "remove":
        return cmd_remove(
            args.id,
            delete=args.delete,
            force=args.force,
            pdir=getattr(args, 'project_dir', None),
        )
    elif args.graph_command == "validate":
        return cmd_validate(
            verbose=args.verbose,
            fix=args.fix,
            coverage=args.coverage,
            pdir=getattr(args, 'project_dir', None),
        )
    elif args.graph_command == "promote":
        return cmd_promote(
            args.draft_id,
            target_id=getattr(args, 'target_id', None),
            force=getattr(args, 'force', False),
            no_merge=getattr(args, 'no_merge', False),
            pdir=getattr(args, 'project_dir', None),
        )
    else:
        parser.print_help()
        return 0
