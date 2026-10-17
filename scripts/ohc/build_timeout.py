"""ci/config/build_timeouts.txt 管理 — CI/W3 构建超时配置的查询与维护。

与 ci/conan/build_and_test.sh 的 build_timeout_for() / validate_build_timeout_config()
保持同构（单一事实源为同一份配置文件）：
  - 条目格式: `name/version 秒数`（精确匹配，无通配符）
  - 条目唯一，秒数为整数，范围 [3600, 57600]
  - 未配置的包使用 DEFAULT_BUILD_TIMEOUT=3600

CLI:
    ohc-run.py timeout get <software> <version>
    ohc-run.py timeout set <software> <version> <seconds> [--force]
    ohc-run.py timeout remove <software>/<version>
    ohc-run.py timeout list
    ohc-run.py timeout validate
"""
from __future__ import annotations

import re
from pathlib import Path

from .utils import find_project_dir, log_fail, log_info, log_ok, log_warn

DEFAULT_BUILD_TIMEOUT = 3600
MAX_BUILD_TIMEOUT = 57600
_ENTRY_RE = re.compile(r"^([A-Za-z0-9._+-]+/[A-Za-z0-9._+-]+)\s+(\d+)$")


def config_path(pdir: str | None = None) -> Path:
    project = Path(pdir) if pdir else Path(find_project_dir())
    return project / "ci" / "config" / "build_timeouts.txt"


def load_entries(pdir: str | None = None) -> list[tuple[str, int, int]]:
    """Load (ref, seconds, line_no) tuples. Malformed lines are skipped
    (use validate() to find them)."""
    path = config_path(pdir)
    if not path.exists():
        return []
    entries: list[tuple[str, int, int]] = []
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENTRY_RE.match(line)
        if m:
            entries.append((m.group(1), int(m.group(2)), line_no))
    return entries


def effective_timeout(software: str, version: str,
                      pdir: str | None = None) -> int:
    """Effective conan-create timeout for software/version (CI 同源配置)."""
    ref = f"{software}/{version}"
    for entry_ref, seconds, _ in load_entries(pdir):
        if entry_ref == ref:
            return seconds
    return DEFAULT_BUILD_TIMEOUT


def local_w3_timeout(software: str, version: str,
                     pdir: str | None = None) -> int:
    """Timeout for local W3 CI simulation.

    Priority: OHC_W3_TIMEOUT env override > build_timeouts.txt > default.
    """
    env_val = __import__("os").environ.get("OHC_W3_TIMEOUT", "").strip()
    if env_val.isdigit():
        return int(env_val)
    return effective_timeout(software, version, pdir)


def validate(pdir: str | None = None) -> list[str]:
    """Validate config file; return list of error strings (empty = valid).

    Mirrors the AWK checks in build_and_test.sh validate_build_timeout_config().
    """
    path = config_path(pdir)
    errors: list[str] = []
    if not path.exists():
        return [f"配置文件不存在: {path}"]
    seen: dict[str, int] = {}
    for line_no, raw in enumerate(path.read_text(encoding="utf-8").split("\n"), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        m = _ENTRY_RE.match(line)
        if not m:
            errors.append(f"第 {line_no} 行格式非法（应为 'name/version 秒数'）: {line}")
            continue
        ref, seconds_str = m.group(1), m.group(2)
        seconds = int(seconds_str)
        if ref in seen:
            errors.append(f"第 {line_no} 行重复条目: {ref}（首次出现于第 {seen[ref]} 行）")
            continue
        seen[ref] = line_no
        if not (DEFAULT_BUILD_TIMEOUT <= seconds <= MAX_BUILD_TIMEOUT):
            errors.append(
                f"第 {line_no} 行 {ref} 超时值 {seconds}s 超出允许范围 "
                f"[{DEFAULT_BUILD_TIMEOUT}, {MAX_BUILD_TIMEOUT}]")
    return errors


# ═══════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════

def _cmd_get(software: str, version: str, pdir: str | None) -> int:
    ref = f"{software}/{version}"
    timeout = effective_timeout(software, version, pdir)
    source = "build_timeouts.txt" if timeout != DEFAULT_BUILD_TIMEOUT else "默认值"
    print(f"{ref}: {timeout}s（来源: {source}）")
    return 0


def _cmd_set(software: str, version: str, seconds: int,
             pdir: str | None, force: bool) -> int:
    ref = f"{software}/{version}"
    path = config_path(pdir)
    if not (DEFAULT_BUILD_TIMEOUT <= seconds <= MAX_BUILD_TIMEOUT):
        log_fail(f"超时值 {seconds}s 超出允许范围 "
                 f"[{DEFAULT_BUILD_TIMEOUT}, {MAX_BUILD_TIMEOUT}]")
        return 1

    entries = load_entries(pdir)
    existing = [e for e in entries if e[0] == ref]
    if existing and not force:
        log_fail(f"{ref} 已有条目 {existing[0][1]}s，如需覆盖请加 --force")
        return 1

    if existing and force:
        # Rewrite the existing line in place
        lines = path.read_text(encoding="utf-8").split("\n")
        for i, raw in enumerate(lines):
            m = _ENTRY_RE.match(raw.strip())
            if m and m.group(1) == ref:
                lines[i] = f"{ref} {seconds}"
        path.write_text("\n".join(lines), encoding="utf-8")
        log_ok(f"✅ 已更新: {ref} {existing[0][1]}s → {seconds}s")
    else:
        with open(path, "a", encoding="utf-8") as f:
            f.write(f"{ref} {seconds}\n")
        log_ok(f"✅ 已追加: {ref} {seconds}s")

    errs = validate(pdir)
    if errs:
        log_warn("⚠️ 配置校验发现问题（CI 端会 fail）:")
        for e in errs:
            log_warn(f"  {e}")
        return 1
    log_ok("配置校验通过（与 CI AWK 校验同构）")
    return 0


def _cmd_remove(ref: str, pdir: str | None) -> int:
    path = config_path(pdir)
    if not path.exists():
        log_fail(f"配置文件不存在: {path}")
        return 1
    lines = path.read_text(encoding="utf-8").split("\n")
    kept = []
    removed = 0
    for raw in lines:
        m = _ENTRY_RE.match(raw.strip())
        if m and m.group(1) == ref:
            removed += 1
            continue
        kept.append(raw)
    if not removed:
        log_fail(f"未找到条目: {ref}")
        return 1
    path.write_text("\n".join(kept), encoding="utf-8")
    log_ok(f"✅ 已删除 {removed} 条: {ref}")
    return 0


def _cmd_list(pdir: str | None) -> int:
    entries = load_entries(pdir)
    if not entries:
        log_info(f"无覆盖条目（全部使用默认 {DEFAULT_BUILD_TIMEOUT}s）")
        return 0
    log_info(f"共 {len(entries)} 条覆盖（默认 {DEFAULT_BUILD_TIMEOUT}s，上限 {MAX_BUILD_TIMEOUT}s）:")
    for ref, seconds, line_no in entries:
        print(f"  {ref:<40} {seconds:>6}s")
    return 0


def _cmd_validate(pdir: str | None) -> int:
    errs = validate(pdir)
    if errs:
        log_fail(f"❌ {len(errs)} 个问题:")
        for e in errs:
            log_fail(f"  {e}")
        return 1
    log_ok("✅ 配置校验通过")
    return 0


def timeout_cli(argv: list[str] | None = None) -> int:
    import argparse
    parser = argparse.ArgumentParser(
        prog="ohc timeout",
        description="管理 ci/config/build_timeouts.txt（CI 与本地 W3 共用的构建超时配置）",
    )
    sub = parser.add_subparsers(dest="action", required=True)

    p_get = sub.add_parser("get", help="查询某包的有效超时（配置或默认）")
    p_get.add_argument("software")
    p_get.add_argument("version")
    p_get.add_argument("--project-dir", "-p", default=None)

    p_set = sub.add_parser("set", help="新增/覆盖超时条目（3600..57600）")
    p_set.add_argument("software")
    p_set.add_argument("version")
    p_set.add_argument("seconds", type=int)
    p_set.add_argument("--force", action="store_true", help="覆盖已有条目")
    p_set.add_argument("--project-dir", "-p", default=None)

    p_rm = sub.add_parser("remove", help="删除超时条目")
    p_rm.add_argument("ref", help="name/version")
    p_rm.add_argument("--project-dir", "-p", default=None)

    sub.add_parser("list", help="列出所有覆盖条目")

    sub.add_parser("validate", help="校验配置（与 CI AWK 校验同构）")

    args = parser.parse_args(argv)
    pdir = getattr(args, "project_dir", None)

    if args.action == "get":
        return _cmd_get(args.software, args.version, pdir)
    if args.action == "set":
        return _cmd_set(args.software, args.version, args.seconds, pdir, args.force)
    if args.action == "remove":
        return _cmd_remove(args.ref, pdir)
    if args.action == "list":
        return _cmd_list(pdir)
    if args.action == "validate":
        return _cmd_validate(pdir)
    return 1
