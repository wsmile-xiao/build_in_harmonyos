#!/usr/bin/env python3
"""Smoke-test the installed comet CLI (clap surface only; never starts the service)."""

import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        print("usage: test_comet.py <comet-binary>", file=sys.stderr)
        return 2
    binary = sys.argv[1]
    failures = []

    def run(name, arguments):
        try:
            result = subprocess.run([binary] + arguments, capture_output=True,
                                    timeout=30, stdin=subprocess.DEVNULL)
        except subprocess.SubprocessError as error:
            print("[FAIL] " + name + ": " + str(error))
            failures.append(name)
            return b"", b""
        print("[STEP] " + name + " rc=" + str(result.returncode))
        print("[stdout] " + result.stdout.decode("utf-8", errors="replace"))
        if result.stderr:
            print("[stderr] " + result.stderr.decode("utf-8", errors="replace"))
        return result.stdout, result.stderr

    version_out, _ = run("version", ["--version"])
    if version_out.strip() == b"comet 0.3.2":
        print("[PASS] exact version")
    else:
        print("[FAIL] exact version (expected 'comet 0.3.2')")
        failures.append("exact version")

    help_out, _ = run("help", ["--help"])
    if b"Usage:" in help_out:
        print("[PASS] usage surface")
    else:
        print("[FAIL] usage surface (no 'Usage:' in --help output)")
        failures.append("usage surface")

    _, err = run("unknown-flag", ["--definitely-not-a-flag"])
    if err:
        print("[PASS] unknown flag rejected with diagnostic")
    else:
        print("[FAIL] unknown flag rejected with diagnostic")
        failures.append("unknown flag diagnostic")

    if failures:
        print("[FAIL] " + ", ".join(failures))
        return 1
    print("[PASS] comet CLI smoke test (3 assertions)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
