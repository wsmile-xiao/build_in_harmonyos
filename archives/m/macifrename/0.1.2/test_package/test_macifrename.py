#!/usr/bin/env python3
"""Runtime checks for the packaged macifrename executable."""

from __future__ import annotations

import os
import subprocess
import sys


def run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=10,
        check=False,
    )


def assert_contains(output: str, expected: str) -> None:
    if expected not in output:
        raise AssertionError(f"expected {expected!r} in output:\n{output}")


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: test_macifrename.py <path-to-macifrename>")

    executable = sys.argv[1]
    assert os.path.isfile(executable), f"missing executable: {executable}"

    help_result = run_command([executable, "-h"])
    assert help_result.returncode == 1, help_result.stdout
    assert_contains(help_result.stdout, "usage: macifrename [-h] [config-file]")

    missing_config = "/tmp/macifrename-conan-test-missing.conf"
    if os.path.exists(missing_config):
        os.unlink(missing_config)
    missing_result = run_command([executable, missing_config])
    assert missing_result.returncode == 1, missing_result.stdout
    assert_contains(missing_result.stdout, "opening config file")
    assert_contains(missing_result.stdout, missing_config)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
