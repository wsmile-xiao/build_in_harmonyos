#!/usr/bin/env python3
"""Consumer driver for GNU Proxyknife 1.7 (R34): run the packaged tool and
assert real behaviour (--version banner, --help usage, unknown-option
rejection)."""
import subprocess
import sys


def run(*args):
    return subprocess.run(args, capture_output=True, text=True)


def main():
    bindir = sys.argv[1]
    exe = bindir.rstrip("/\\") + "/proxyknife"
    failures = 0

    ver = run(exe, "--version")
    if ver.returncode == 0 and "GNU Proxyknife 1.7" in ver.stdout:
        print("PASS: --version reports GNU Proxyknife 1.7")
    else:
        print(f"FAIL: --version rc={ver.returncode} out={ver.stdout!r} err={ver.stderr!r}")
        failures += 1

    help_out = run(exe, "--help")
    if help_out.returncode == 0 and "Usage: proxyknife" in help_out.stdout:
        print("PASS: --help prints usage")
    else:
        print(f"FAIL: --help rc={help_out.returncode} out={help_out.stdout!r}")
        failures += 1

    bad = run(exe, "--no-such-option")
    if bad.returncode != 0 and "unrecognized option" in (bad.stdout + bad.stderr):
        print("PASS: unknown option is rejected with non-zero exit")
    else:
        print(f"FAIL: unknown option rc={bad.returncode} out={bad.stdout!r} err={bad.stderr!r}")
        failures += 1

    if failures:
        print(f"{failures} check(s) FAILED")
        return 1
    print("proxyknife consumer test: all checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
