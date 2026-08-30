#!/usr/bin/env python3
"""Conan test_package for dpkg — verifies the dpkg binary exists AND runs.

R34 consumer check (AI review P2 fix): dpkg is package_type = "application",
the verifiable artifact is the installed binary under <pkg>/bin/.
Previously only checked os.path.isfile (empty-shell risk — a zero-byte /
corrupt / wrong-arch / missing-dependency binary would falsely pass).
Now ALSO executes `dpkg --version` to prove the binary is runnable.
"""
import os
import subprocess
import sys


def main():
    pkg = sys.argv[1]
    bin_dir = os.path.join(pkg, "bin")
    dpkg_bin = os.path.join(bin_dir, "dpkg")
    if not os.path.isfile(dpkg_bin):
        print(f"FAIL: dpkg binary not found: {dpkg_bin}")
        return 1
    # P2 修复：实际执行二进制（--version 不触碰系统，安全）
    r = subprocess.run([dpkg_bin, "--version"], capture_output=True,
                       text=True)
    if r.returncode != 0:
        print(f"FAIL: dpkg --version rc={r.returncode}: "
              f"{r.stderr.strip()[:300]}", file=sys.stderr)
        return 1
    ver = (r.stdout or r.stderr).strip().splitlines()
    print(f"OK: dpkg binary present + runnable: {ver[0] if ver else dpkg_bin}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
