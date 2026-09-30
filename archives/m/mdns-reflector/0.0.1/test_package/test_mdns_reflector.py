#!/usr/bin/env python3
"""Exercise the installed mdns-reflector binary.

Runs only argument-parsing paths that need no network interfaces or
multicast privileges: `-h` must succeed with the version banner and
usage text, and an argument-less invocation must exit non-zero.
"""

import pathlib
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_mdns_reflector.py <mdns-reflector>")

    executable = pathlib.Path(sys.argv[1]).resolve()
    assert executable.is_file(), f"missing executable: {executable}"

    help_result = subprocess.run(
        [str(executable), "-h"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    assert help_result.returncode == 0, (
        f"-h exited {help_result.returncode}\n"
        f"stdout:\n{help_result.stdout}\nstderr:\n{help_result.stderr}"
    )
    assert "mDNS Reflector version" in help_result.stdout, help_result.stdout
    assert "usage:" in help_result.stdout, help_result.stdout
    assert "IFNAME" in help_result.stdout, help_result.stdout

    usage_result = subprocess.run(
        [str(executable)],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    assert usage_result.returncode != 0, (
        "argument-less invocation should exit non-zero, got 0"
    )

    bad_flag = subprocess.run(
        [str(executable), "-Z"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,
    )
    assert bad_flag.returncode != 0, (
        "unknown option -Z should exit non-zero, got 0"
    )

    print(
        "mdns-reflector consumer test passed: "
        "version banner, usage text, and error paths"
    )


if __name__ == "__main__":
    main()
