"""Requirements graph — 系统能力需求跟踪

跟踪鸿蒙PC平台缺失的能力，当系统支持后可关闭。

结构类似知识图谱，每个条目记录:
- 缺什么能力 (needed_capability)
- 哪些软件受影响 (affected_software)
- 当前变通方案 (current_workaround)
- 状态 (open/closed)
- 关闭版本 (closed_in_version)

生命周期:
  预分析/编译/测试发现系统能力缺失 → req add → open
  系统更新支持该能力 → req close → closed
"""
from __future__ import annotations

import os
import re
import sys
from datetime import date
from pathlib import Path

_TEMPLATE = """id:                     R{NNN}
title:                  {title}
category:               {category}
severity:               {severity}
status:                 open
affected_software:      {software}
description:            {description}
needed_capability:      {needed}
current_workaround:     {workaround}
created_date:           {date}
closed_in_version:      
closed_date:            
contributors:           {contributor}
"""

REQUIRED_FIELDS = ["id", "title", "category", "status", "affected_software",
                   "description", "needed_capability", "created_date"]

VALID_CATEGORIES = ["graphics", "audio", "video", "ipc", "filesystem",
                    "shell", "toolchain", "syscall", "network", "security",
                    "signing", "runtime", "other"]


def _find_project_dir() -> Path:
    d = Path.cwd()
    for _ in range(10):
        if (d / "SKILL.md").exists():
            return d
        d = d.parent
    return Path.cwd()


def _req_dir(pdir: str | None = None) -> Path:
    project = Path(pdir) if pdir else _find_project_dir()
    rdir = project / "knowledge" / "requirements"
    rdir.mkdir(parents=True, exist_ok=True)
    return rdir


def _next_id(rdir: Path) -> str:
    existing = set()
    for f in rdir.glob("R*.kv"):
        if re.match(r'^R\d+\.kv$', f.name):
            existing.add(f.stem)
    n = 1
    while f"R{n:03d}" in existing:
        n += 1
    return f"R{n:03d}"


def _get_git_author() -> str:
    import subprocess
    try:
        r = subprocess.run(["git", "config", "user.name"], capture_output=True, text=True, timeout=5)
        return r.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def cmd_add(
    *,
    title: str,
    category: str,
    severity: str = "2",
    software: str = "",
    description: str = "",
    needed: str = "",
    workaround: str = "",
    pdir: str | None = None,
) -> int:
    rdir = _req_dir(pdir)
    rid = _next_id(rdir)
    author = _get_git_author()

    if category not in VALID_CATEGORIES:
        print(f"⚠️ 类别 '{category}' 非标准，有效类别: {', '.join(VALID_CATEGORIES)}")

    content = _TEMPLATE.format(
        NNN=rid.split("-")[1] if "-" in rid else rid[1:],
        title=title, category=category, severity=severity,
        software=software or "*", description=description,
        needed=needed, workaround=workaround,
        date=str(date.today()), contributor=author,
    )
    # Fix id line
    content = content.replace(f"R{rid.split('-')[1] if '-' in rid else rid[1:]}", rid, 1)

    path = rdir / f"{rid}.kv"
    path.write_text(content, encoding="utf-8")
    print(f"✅ 需求条目: {path}")
    print(f"   ID: {rid}")
    print(f"   状态: open")
    print(f"   标题: {title}")
    return 0


def cmd_list(
    *,
    status_filter: str = "all",
    pdir: str | None = None,
) -> int:
    rdir = _req_dir(pdir)
    entries = []
    for f in sorted(rdir.glob("R*.kv")):
        if not re.match(r'^R\d+\.kv$', f.name):
            continue
        fields = {}
        for line in f.read_text(encoding="utf-8").split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^(\w+):\s*(.*)', line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()
        st = fields.get('status', 'unknown')
        if status_filter != "all" and st != status_filter:
            continue
        entries.append(fields)

    if not entries:
        print("（无需求条目）" if status_filter == "all" else f"（无 {status_filter} 需求）")
        return 0

    print(f"{'ID':<8} {'状态':<8} {'严重度':<6} {'类别':<12} {'标题':<40} {'受影响软件'}")
    print("-" * 100)
    for e in entries:
        print(f"{e.get('id','?'):<8} {e.get('status','?'):<8} {e.get('severity','?'):<6} "
              f"{e.get('category','?'):<12} {e.get('title','?')[:40]:<40} {e.get('affected_software','?')}")

    open_count = sum(1 for e in entries if e.get('status') == 'open')
    closed_count = sum(1 for e in entries if e.get('status') == 'closed')
    print(f"\n共 {len(entries)} 条: {open_count} open, {closed_count} closed")
    return 0


def cmd_close(
    rid: str,
    *,
    version: str = "",
    pdir: str | None = None,
) -> int:
    rdir = _req_dir(pdir)
    path = rdir / f"{rid}.kv"
    if not path.exists():
        print(f"❌ 需求不存在: {rid}")
        return 1

    content = path.read_text(encoding="utf-8")
    content = re.sub(r'^status:.*$', 'status:                 closed', content, flags=re.MULTILINE)
    content = re.sub(r'^closed_in_version:.*$', f'closed_in_version:      {version}', content, flags=re.MULTILINE)
    content = re.sub(r'^closed_date:.*$', f'closed_date:            {date.today()}', content, flags=re.MULTILINE)
    path.write_text(content, encoding="utf-8")
    print(f"✅ {rid} 已关闭 (版本: {version or '未指定'})")
    return 0


def cmd_validate(*, pdir: str | None = None) -> int:
    rdir = _req_dir(pdir)
    errors = 0
    warnings = 0

    files = [f for f in sorted(rdir.glob("R*.kv")) if re.match(r'^R\d+\.kv$', f.name)]
    print(f"🔍 Requirements Validation ({len(files)} entries)")

    for f in files:
        fields = {}
        for line in f.read_text(encoding="utf-8").split('\n'):
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            m = re.match(r'^(\w+):\s*(.*)', line)
            if m and m.group(1) not in fields:
                fields[m.group(1)] = m.group(2).strip()

        # Check required fields
        missing = [fld for fld in REQUIRED_FIELDS if fld not in fields or not fields[fld].strip()]
        if missing:
            print(f"  ❌ {f.stem}: missing fields: {missing}")
            errors += 1

        # Check status
        st = fields.get('status', '')
        if st not in ('open', 'closed'):
            print(f"  ❌ {f.stem}: invalid status '{st}'")
            errors += 1

        # Check closed entries have closed_date
        if st == 'closed' and not fields.get('closed_date', '').strip():
            print(f"  ⚠️ {f.stem}: closed but no closed_date")
            warnings += 1

    if errors:
        print(f"\n❌ {errors} errors, {warnings} warnings")
    else:
        print(f"\n✅ All checks passed ({warnings} warnings)")
    return 1 if errors else 0


def req_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(prog="ohc req", description="系统能力需求管理")
    sub = parser.add_subparsers(dest="req_command")

    # add
    p_add = sub.add_parser("add", help="新增需求条目")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--category", required=True)
    p_add.add_argument("--severity", default="2")
    p_add.add_argument("--software", default="")
    p_add.add_argument("--description", default="")
    p_add.add_argument("--needed", default="")
    p_add.add_argument("--workaround", default="")
    p_add.add_argument("--project-dir")

    # list
    p_list = sub.add_parser("list", help="列出需求条目")
    p_list.add_argument("--status", choices=["open", "closed", "all"], default="all")
    p_list.add_argument("--project-dir")

    # close
    p_close = sub.add_parser("close", help="关闭需求")
    p_close.add_argument("id", help="需求ID (e.g. R001)")
    p_close.add_argument("--version", default="")
    p_close.add_argument("--project-dir")

    # validate
    p_val = sub.add_parser("validate", help="一致性校验")
    p_val.add_argument("--project-dir")

    args = parser.parse_args(argv)

    if args.req_command == "add":
        return cmd_add(title=args.title, category=args.category, severity=args.severity,
                       software=args.software, description=args.description,
                       needed=args.needed, workaround=args.workaround,
                       pdir=getattr(args, 'project_dir', None))
    elif args.req_command == "list":
        return cmd_list(status_filter=args.status, pdir=getattr(args, 'project_dir', None))
    elif args.req_command == "close":
        return cmd_close(args.id, version=args.version, pdir=getattr(args, 'project_dir', None))
    elif args.req_command == "validate":
        return cmd_validate(pdir=getattr(args, 'project_dir', None))
    else:
        parser.print_help()
        return 0
