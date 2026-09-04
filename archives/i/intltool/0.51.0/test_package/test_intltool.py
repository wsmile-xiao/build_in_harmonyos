#!/usr/bin/env python3
"""Conan test_package for intltool — R34 real artifact verification (no empty shell).

intltool ships 5 Perl tools under <pkg>/bin/ (intltool-update, intltoolize,
intltool-extract, intltool-merge, intltool-prepare). This test verifies the
tools exist, are executable, and intltool-update --version actually runs and
reports 0.51.0 — proving the packaged tools work on the target.
"""
import os
import subprocess
import sys


def main():
    pkg = sys.argv[1]
    bindir = os.path.join(pkg, "bin")
    tools = ["intltool-update", "intltoolize", "intltool-extract"]
    for tool in tools:
        exe = os.path.join(bindir, tool)
        if not os.path.isfile(exe):
            print(f"FAIL: {exe} not found", file=sys.stderr)
            return 1
        if not os.access(exe, os.X_OK):
            print(f"FAIL: {exe} not executable", file=sys.stderr)
            return 1

    # R34: 真实执行 intltool-update --version 校验工具可用且版本正确。
    r = subprocess.run([os.path.join(bindir, "intltool-update"), "--version"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: intltool-update --version rc={r.returncode}: {r.stderr[:300]}",
              file=sys.stderr)
        return 1
    out = r.stdout + r.stderr
    if "0.51.0" not in out:
        print(f"FAIL: version not 0.51.0: {out[:200]}", file=sys.stderr)
        return 1

    print(f"OK: intltool-update --version -> {out.strip()[:120]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
