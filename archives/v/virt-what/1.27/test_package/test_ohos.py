#!/usr/bin/env python3
"""HarmonyOS-specific runtime test for virt-what's best-effort detection."""

import os
import re
import subprocess
import sys
import platform


def check(label, condition, detail=""):
    if not condition:
        raise SystemExit(f"FAIL: {label}: {detail}")
    print(f"PASS: {label}")


def main():
    bindir = os.path.abspath(sys.argv[1])
    script = os.path.join(bindir, "virt-what")
    env = os.environ.copy()
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")

    check("test executes on HarmonyOS", platform.system() == "HarmonyOS", platform.system())
    check("test executes on AArch64", platform.machine().lower() in ("aarch64", "arm64"), platform.machine())

    result = subprocess.run(
        [script], capture_output=True, text=True, env=env, timeout=10
    )
    check("real HarmonyOS detection exits successfully", result.returncode == 0, result.stderr)
    facts = [line for line in result.stdout.splitlines() if line]
    valid = all(re.fullmatch(r"[a-z0-9][a-z0-9_-]*", line) for line in facts)
    check("detection output contains only virt-what facts", valid, result.stdout)


if __name__ == "__main__":
    main()
