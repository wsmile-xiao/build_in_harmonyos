#!/usr/bin/env python3
"""Smoke test for xapers 0.9.0 — exercises the installed package.

Verifies that:
1. The `xapers` CLI is installed and responds to --version
2. The `xapers` Python package imports and its version module works

R34: test must substantively exercise the package (run the binary / API).
"""
import os
import shutil
import subprocess
import sys

failures = []


def check(name, cond, detail=""):
    if cond:
        print(f"  PASS  {name}")
    else:
        print(f"  FAIL  {name}  {detail}")
        failures.append(name)


# 1. The xapers Python package is importable and reports the right version
print("[test] import xapers")
try:
    import xapers
    from xapers import version
    check("xapers import", True)
    check("xapers version", version.__version__ == "0.9.0",
          f"got {version.__version__}")
except Exception as e:
    check("xapers import", False, str(e))

# 2. The xapers CLI binary is on PATH and responds to --version
print("[test] xapers --version")
xapers_bin = shutil.which("xapers")
if xapers_bin is None:
    check("xapers --version", False, "binary not found on PATH")
else:
    try:
        out = subprocess.run([xapers_bin, "--version"],
                             capture_output=True, text=True, timeout=60)
        ok = out.returncode == 0 and "xapers" in (out.stdout + out.stderr)
        check("xapers --version", ok, out.stdout + out.stderr)
    except Exception as e:
        check("xapers --version", False, str(e))

if failures:
    print(f"\n{len(failures)} test(s) FAILED: {', '.join(failures)}")
    sys.exit(1)
print("\nAll tests passed.")
