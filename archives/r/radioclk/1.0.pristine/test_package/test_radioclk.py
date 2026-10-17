#!/usr/bin/env python3
"""Consumer assertions for the installed radioclk/1.0.pristine package.

Exercises only deterministic, hardware-free code paths of radioclkd:
argument parsing, version/usage output and the two early error paths
(no serial port argument, unopenable device). None of these touch a real
serial port, SysV shared memory or the system logger.
"""
import subprocess
import sys

EXPECTED_VERSION = "radioclkd version 1.0"
EXPECTED_USAGE = "Usage: radioclkd"
EXPECTED_NO_DEVICE = "no serial port specified"
EXPECTED_OPEN_FAIL = "couldn't open device"


def run(binary, args):
    return subprocess.run(
        [binary] + args,
        capture_output=True,
        text=True,
        timeout=30,
    )


def main():
    binary = sys.argv[1]

    # 1. --version prints the version banner and exits 0
    result = run(binary, ["--version"])
    assert result.returncode == 0, (
        f"--version exit code {result.returncode}, stderr={result.stderr!r}")
    assert EXPECTED_VERSION in result.stdout, (
        f"version banner missing from stdout: {result.stdout!r}")

    # 2. -v short form is equivalent
    result = run(binary, ["-v"])
    assert result.returncode == 0
    assert EXPECTED_VERSION in result.stdout

    # 3. --help prints usage and exits 0
    result = run(binary, ["--help"])
    assert result.returncode == 0, (
        f"--help exit code {result.returncode}, stderr={result.stderr!r}")
    assert EXPECTED_USAGE in result.stdout, (
        f"usage banner missing from stdout: {result.stdout!r}")

    # 4. no arguments: early error before any device access
    result = run(binary, [])
    assert result.returncode == 1, (
        f"no-arg exit code {result.returncode}")
    assert EXPECTED_NO_DEVICE in result.stderr, (
        f"expected no-device diagnostic, stderr={result.stderr!r}")

    # 5. nonexistent device path: early error on open()
    result = run(binary, ["/dev/radioclk-does-not-exist"])
    assert result.returncode == 1, (
        f"bad-device exit code {result.returncode}")
    assert EXPECTED_OPEN_FAIL in result.stderr, (
        f"expected open-failure diagnostic, stderr={result.stderr!r}")

    print("test_radioclk: all 5 assertion groups passed")


if __name__ == "__main__":
    main()
