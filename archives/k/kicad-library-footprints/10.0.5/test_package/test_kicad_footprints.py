#!/usr/bin/env python3
"""Consumer validation for the KiCad 10.0.5 footprint resource package."""

import argparse
import os
import re
import sys
import tempfile
from pathlib import Path


FOOTPRINT_ROOT = Path("share") / "kicad" / "footprints"
TABLE_PATH = Path("share") / "kicad" / "template" / "fp-lib-table"
LICENSE_PATH = Path("licenses") / "LICENSE.md"
VERSION_RE = re.compile(r"\(version\s+(\d+)\)")
LAYER_RE = re.compile(r"\(layer\s+\"[^\"]+\"\)")
LIB_RE = re.compile(
    r"\(lib\s+\(name\s+\"([^\"]+)\".*?"
    r"\(uri\s+\"\$\{KICAD10_FOOTPRINT_DIR\}/([^\"]+)\"",
    re.DOTALL,
)


class Checker:
    """Collect assertion results while preserving a useful final summary."""

    def __init__(self):
        self.passed = 0
        self.failed = 0

    def check(self, condition, label, detail=""):
        if condition:
            self.passed += 1
            return True
        self.failed += 1
        suffix = f" — {detail}" if detail else ""
        print(f"  [FAIL] {label}{suffix}")
        return False

    @property
    def total(self):
        return self.passed + self.failed


def sexpr_balanced(text):
    """Return whether parentheses are balanced outside quoted strings."""
    depth = 0
    in_string = False
    escaped = False
    for char in text:
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth < 0:
                return False
    return not in_string and depth == 0


def validate_footprint(path):
    """Return an error string for a malformed KiCad footprint, or None."""
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        return f"cannot read {path}: {exc}"
    if not text.lstrip().startswith("(footprint "):
        return "root is not (footprint ...)"
    if not VERSION_RE.search(text):
        return "missing numeric (version ...) field"
    if not LAYER_RE.search(text):
        return "missing (layer ...) field"
    if not sexpr_balanced(text):
        return "unbalanced or unterminated s-expression"
    return None


def parse_table(path):
    """Return table library names and URIs from an fp-lib-table file."""
    text = path.read_text(encoding="utf-8")
    if not text.lstrip().startswith("(fp_lib_table"):
        raise ValueError("root is not (fp_lib_table ...)")
    if not sexpr_balanced(text):
        raise ValueError("fp-lib-table has unbalanced parentheses")
    entries = [(name, uri) for name, uri in LIB_RE.findall(text)]
    if not entries:
        raise ValueError("fp-lib-table contains no library entries")
    return entries


def check_package(package_folder, ohos):
    checker = Checker()
    package_root = Path(package_folder)
    footprints = package_root / FOOTPRINT_ROOT
    table = package_root / TABLE_PATH
    license_file = package_root / LICENSE_PATH

    checker.check(
        footprints.is_dir(),
        "footprint resource directory exists",
        str(footprints),
    )
    if not footprints.is_dir():
        return checker

    checker.check(table.is_file(), "fp-lib-table exists", str(table))
    checker.check(license_file.is_file(), "LICENSE.md is installed", str(license_file))
    if not table.is_file():
        return checker

    pretty_dirs = sorted(
        path for path in footprints.iterdir() if path.is_dir() and path.name.endswith(".pretty")
    )
    footprint_files = sorted(footprints.glob("*.pretty/**/*.kicad_mod"))
    checker.check(bool(pretty_dirs), "at least one .pretty library is installed")
    checker.check(bool(footprint_files), "at least one .kicad_mod is installed")
    if not pretty_dirs or not footprint_files:
        return checker

    try:
        entries = parse_table(table)
    except (OSError, UnicodeError, ValueError) as exc:
        checker.check(False, "fp-lib-table parses", str(exc))
        return checker

    table_dirs = {uri.rsplit("/", 1)[-1] for _, uri in entries}
    installed_dirs = {path.name for path in pretty_dirs}
    checker.check(
        table_dirs == installed_dirs,
        "fp-lib-table exactly matches installed libraries",
        f"table={len(table_dirs)} installed={len(installed_dirs)}",
    )

    for path in footprint_files:
        checker.check(validate_footprint(path) is None, "footprint parses", str(path))

    temp_parent = None
    try:
        if ohos:
            tmpdir = os.environ.get("TMPDIR", "")
            checker.check(bool(tmpdir), "OHOS TMPDIR is defined")
            checker.check(
                os.path.abspath(tmpdir).rstrip("/") != "/tmp",
                "OHOS TMPDIR avoids read-only /tmp",
                tmpdir,
            )
            if not tmpdir or os.path.abspath(tmpdir).rstrip("/") == "/tmp":
                return checker
            Path(tmpdir).mkdir(parents=True, exist_ok=True)
            temp_parent = tempfile.TemporaryDirectory(dir=tmpdir)
        else:
            temp_parent = tempfile.TemporaryDirectory()
        truncated = Path(temp_parent.name) / "truncated.kicad_mod"
        truncated.write_text(footprint_files[0].read_text(encoding="utf-8")[:128], encoding="utf-8")
        checker.check(
            validate_footprint(truncated) is not None,
            "truncated footprint is rejected",
        )
    finally:
        if temp_parent is not None:
            temp_parent.cleanup()

    return checker


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("package_folder")
    parser.add_argument("--ohos", action="store_true")
    args = parser.parse_args(argv)

    try:
        checker = check_package(args.package_folder, args.ohos)
    except (OSError, UnicodeError, ValueError) as exc:
        print(f"[FAIL] consumer validation error: {exc}")
        return 1
    print(f"kicad-library-footprints consumer: {checker.passed}/{checker.total} assertions passed")
    return 0 if checker.failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
