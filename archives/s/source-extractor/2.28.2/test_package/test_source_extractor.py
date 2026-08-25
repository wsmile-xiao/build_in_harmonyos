#!/usr/bin/env python3
"""source-extractor consumer test (L0c + R34): run sex/ldactoasc --version.

R34: actually invoke the tested CLI binaries (real command execution).
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <bindir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    sex = os.path.join(bindir, "sex")
    if not os.path.isfile(sex):
        raise AssertionError(f"sex missing in {bindir}")
    # R34: sex --version 真实 CLI 调用（上游实现输出版本后 exit 0）
    r = subprocess.run([sex, "--version"], capture_output=True, text=True,
                       timeout=60)
    if r.returncode != 0:
        raise AssertionError(f"sex --version rc={r.returncode}: {r.stderr[:200]}")
    combined = (r.stdout + r.stderr).lower()
    if "version" not in combined or "2.28.2" not in combined:
        raise AssertionError(f"sex --version unexpected output: {combined[:200]}")
    print("OK: sex --version ->", (r.stdout or r.stderr).strip())
    # ldactoasc 辅助二进制同样存在可执行
    ldac = os.path.join(bindir, "ldactoasc")
    if not os.path.isfile(ldac):
        raise AssertionError(f"ldactoasc missing in {bindir}")
    r2 = subprocess.run([ldac, "--help"], capture_output=True, text=True,
                        timeout=60)
    if "syntax" not in ((r2.stdout + r2.stderr).lower()):
        raise AssertionError("ldactoasc --help unexpected output")
    print("OK: ldactoasc --help (syntax usage)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
