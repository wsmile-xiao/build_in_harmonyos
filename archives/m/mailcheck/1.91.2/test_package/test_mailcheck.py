#!/usr/bin/env python3
"""Package-level supplementary test for mailcheck 1.91.2.

Upstream mailcheck 1.91.2 ships NO test suite — the Makefile defines only
all/debug/install/clean targets, with no check or test target, and there is
no tests/ directory, no configure script, and no CI configuration in the
release tarball. This script is a PACKAGE-LEVEL supplementary test, NOT an
upstream test.

It creates a real mbox file and .mailcheckrc, runs the mailcheck binary,
and verifies three assertions:
  1. Exit code is 0.
  2. stdout contains "mail in" (the core functional output).
  3. stdout contains the mbox path that was listed in .mailcheckrc.
"""
import os
import shutil
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        print("usage: test_mailcheck.py <mailcheck_binary>", file=sys.stderr)
        sys.exit(2)
    executable = sys.argv[1]

    tmpdir = tempfile.mkdtemp(prefix="mailcheck_test_")

    try:
        # 1. Create a real mbox file with content (non-zero size)
        mbox_path = os.path.join(tmpdir, "mbox")
        with open(mbox_path, "w") as f:
            f.write("From sender@example.com Mon Jan 1 12:00:00 2024\n")
            f.write("From: sender@example.com\n")
            f.write("Subject: Test message\n\n")
            f.write("Hello, this is a test message.\n")

        # 2. Create .mailcheckrc pointing to the mbox
        rc_path = os.path.join(tmpdir, ".mailcheckrc")
        with open(rc_path, "w") as f:
            f.write(mbox_path + "\n")

        # 3. Run mailcheck with HOME set to tmpdir so it finds .mailcheckrc
        env = dict(os.environ)
        env["HOME"] = tmpdir

        result = subprocess.run(
            [executable],
            capture_output=True,
            text=True,
            env=env,
        )

        print(f"[mailcheck] exit code: {result.returncode}")
        print(f"[mailcheck] stdout: {result.stdout!r}")
        print(f"[mailcheck] stderr: {result.stderr!r}")

        # Assertion 1: exit code must be 0
        if result.returncode != 0:
            print(
                f"FAIL: mailcheck exited with code {result.returncode}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Assertion 2: stdout must contain "mail in" (the core output)
        if "mail in" not in result.stdout:
            print(
                f"FAIL: expected 'mail in' in stdout, got: {result.stdout!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        # Assertion 3: stdout must contain the mbox path
        if mbox_path not in result.stdout:
            print(
                f"FAIL: expected mbox path '{mbox_path}' in stdout, "
                f"got: {result.stdout!r}",
                file=sys.stderr,
            )
            sys.exit(1)

        print("PASS: mailcheck correctly reports mail in mbox")
        print(f"  Output: {result.stdout.strip()}")
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


if __name__ == "__main__":
    main()
