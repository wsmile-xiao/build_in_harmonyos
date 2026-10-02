#!/usr/bin/env python3
"""Consumer-level checks that execute the installed virt-what tools."""

import os
import subprocess
import sys


def check(label, condition, detail=""):
    if not condition:
        raise SystemExit(f"FAIL: {label}: {detail}")
    print(f"PASS: {label}")


def main():
    bindir = os.path.abspath(sys.argv[1])
    script = os.path.join(bindir, "virt-what")
    helper = os.path.join(bindir, "virt-what-cpuid-helper")
    env = os.environ.copy()
    env["PATH"] = bindir + os.pathsep + env.get("PATH", "")

    version = subprocess.run(
        [script, "--version"], capture_output=True, text=True, env=env
    )
    check("virt-what --version exits successfully", version.returncode == 0, version.stderr)
    check("virt-what reports 1.27", version.stdout.strip() == "1.27", version.stdout)

    help_result = subprocess.run(
        [script, "--help"], capture_output=True, text=True, env=env
    )
    check("virt-what --help exits successfully", help_result.returncode == 0, help_result.stderr)
    check("virt-what help documents --version", "--version" in help_result.stdout)

    helper_result = subprocess.run([helper], capture_output=True, text=True, env=env)
    check("packaged CPUID helper runs", helper_result.returncode == 0, helper_result.stderr)


if __name__ == "__main__":
    main()
