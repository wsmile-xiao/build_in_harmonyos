#!/usr/bin/env python3
"""CLI-surface assertions for the packaged yaku-ns commands (5 assertions).

Runs against the delivered binaries and nothing else:

  1. yaku-ns --version prints "yaku-ns <version>" and exits 0
  2. yaku-getzone --version prints "yaku-getzone <version>" and exits 0
  3. yaku-ns --help exits 0 and prints the upstream usage line
  4. yaku-getzone --help exits 0 and prints the upstream usage line
  5. an unknown long option is rejected with exit status 1 on both commands

Assertion 5 is what proves the option parser is still doing its job: a recipe
that swallowed every argument would also satisfy assertions 1-4.

Output is scanned line by line rather than with a prefix match: the loader may
print relocation or preload notices on stderr before the program says anything,
and those notices are not the program's output.  The exit status and the presence
of the expected line are what this test asserts.
"""

import subprocess
import sys

ASSERTIONS = 5


def run(args):
    proc = subprocess.run(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          text=True, timeout=30)
    return proc.returncode, proc.stdout


def has_line(output, expected_prefix):
    """True when some line of the output starts with the expected prefix.

    Line-oriented on purpose: dynamic loaders and the OHOS signer may prepend
    notices to the program's own output, so a plain prefix match on the whole
    stream would be at the mercy of the environment.
    """
    for line in output.splitlines():
        if line.strip().startswith(expected_prefix):
            return True
    return False


def check(index, description, condition, detail=""):
    if condition:
        print("PASS [%d/%d] %s" % (index, ASSERTIONS, description))
        return 0
    print("FAIL [%d/%d] %s" % (index, ASSERTIONS, description))
    if detail:
        print(detail)
    return 1


def main():
    daemon, getzone = sys.argv[1], sys.argv[2]
    failures = 0

    rc, out = run([daemon, "--version"])
    failures += check(1, "yaku-ns --version exits 0 and names the program",
                      rc == 0 and has_line(out, "yaku-ns "),
                      "rc=%d output=%r" % (rc, out))

    rc, out = run([getzone, "--version"])
    failures += check(2, "yaku-getzone --version exits 0 and names the program",
                      rc == 0 and has_line(out, "yaku-getzone "),
                      "rc=%d output=%r" % (rc, out))

    rc, out = run([daemon, "--help"])
    failures += check(3, "yaku-ns --help exits 0 and prints the usage line",
                      rc == 0 and has_line(out, "usage: yaku-ns "),
                      "rc=%d output=%r" % (rc, out))

    rc, out = run([getzone, "--help"])
    failures += check(4, "yaku-getzone --help exits 0 and prints the usage line",
                      rc == 0 and has_line(out, "usage: yaku-getzone -z <zone>"),
                      "rc=%d output=%r" % (rc, out))

    rc_daemon, out_daemon = run([daemon, "--definitely-not-an-option"])
    rc_getzone, out_getzone = run([getzone, "--definitely-not-an-option"])
    failures += check(5, "an unknown long option is rejected with exit status 1",
                      rc_daemon == 1 and rc_getzone == 1,
                      "yaku-ns rc=%d output=%r; yaku-getzone rc=%d output=%r"
                      % (rc_daemon, out_daemon, rc_getzone, out_getzone))

    if failures:
        print("test_cli: %d/%d assertions FAILED" % (failures, ASSERTIONS))
        return 1
    print("test_cli: %d/%d assertions passed" % (ASSERTIONS, ASSERTIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
