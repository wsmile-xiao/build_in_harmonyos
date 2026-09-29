#!/usr/bin/env python3
"""Consumer smoke checks for the packaged kyua binary.

Three real-behavior checks (no stubs):
  1. version: `kyua about version` exits 0 with non-empty output mentioning
     kyua (this snapshot has no `--version` flag: cli/main.cpp registers an
     `about` subcommand and unknown options exit 3, so `--version` can
     never pass here; `about version` is the upstream version interface).
  2. help: `kyua help` exits 0 and lists the `test` command.
  3. smoke-test: builds a minimal Kyuafile + plain test program in a fresh
     temp dir, runs `kyua test`, and requires the deterministic summary
     `1/1 passed (0 failed)` (format proven in cli/cmd_test.cpp).

Each passing check prints exactly one `SMOKE-PASS <name>` line; any failure
prints `SMOKE-FAIL <name>: <reason>` and exits non-zero. The conanfile
counts SMOKE-PASS lines for the HMBS_TEST_PACKAGE_RESULT marker.
"""

import os
import re
import subprocess
import sys
import tempfile

KYUAFILE = """syntax(2)

test_suite("smoke")

plain_test_program{name="pass_test"}
"""

PASS_TEST = """#!/bin/sh
# Minimal kyua plain test program: exit code 0 means pass.
exit 0
"""


def run(cmd, cwd=None):
    proc = subprocess.run(
        cmd,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=300,
    )
    return proc.returncode, proc.stdout or ""


def check_version(kyua):
    rc, out = run([kyua, "about", "version"])
    if rc != 0:
        tail = "\n".join((out or "").splitlines()[-8:])
        return False, "exit code %d out: %s" % (rc, tail)
    if not out.strip():
        return False, "empty output (refusing hollow pass)"
    if "kyua" not in out.lower():
        return False, "output does not mention kyua: %r" % out.strip()[-200:]
    if not re.search(r"\d", out):
        return False, "output has no version digits: %r" % out.strip()[-200:]
    return True, out.strip().splitlines()[0][:120]


def check_help(kyua):
    rc, out = run([kyua, "help"])
    if rc != 0:
        return False, "exit code %d" % rc
    if not out.strip():
        return False, "empty output (refusing hollow pass)"
    if "test" not in out:
        return False, "help does not list the test command"
    return True, "help lists test command"


def check_smoke_test(kyua):
    work = tempfile.mkdtemp(prefix="kyua-smoke-")
    with open(os.path.join(work, "Kyuafile"), "w", encoding="utf-8",
              newline="\n") as handle:
        handle.write(KYUAFILE)
    prog = os.path.join(work, "pass_test")
    # Request the exec bit at creation time: HMDFS may ignore chmod(2), so
    # creation mode is the reliable channel (librb shim precedent).
    fd = os.open(prog, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o755)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(PASS_TEST)
    except Exception:
        try:
            os.close(fd)
        except Exception:
            pass
        raise
    try:
        os.chmod(prog, 0o755)
    except Exception:
        pass
    if not os.access(prog, os.X_OK):
        return False, "pass_test is not executable on this filesystem"
    rc, out = run([kyua, "test"], cwd=work)
    if not out.strip():
        return False, "kyua test produced no output (refusing hollow pass)"
    if not re.search(r"^1/1 passed \(0 failed\)\s*$", out, flags=re.M):
        tail = "\n".join(out.splitlines()[-15:])
        return False, "summary `1/1 passed (0 failed)` missing, rc=%d tail: %s" % (rc, tail)
    if rc != 0:
        return False, "summary ok but exit code %d" % rc
    return True, "1/1 passed (0 failed)"


def main():
    if len(sys.argv) != 2:
        print("usage: test_kyua.py <kyua-bin-dir>")
        return 2
    kyua = os.path.join(sys.argv[1], "kyua")
    if not os.path.isfile(kyua):
        print("SMOKE-FAIL setup: kyua binary missing: %s" % kyua)
        return 1
    checks = (
        ("version", check_version),
        ("help", check_help),
        ("smoke-test", check_smoke_test),
    )
    failed = 0
    for name, func in checks:
        try:
            ok, detail = func(kyua)
        except Exception as exc:  # noqa: BLE001 - report, never crash silent
            ok, detail = False, "exception: %s" % exc
        if ok:
            print("SMOKE-PASS %s: %s" % (name, detail), flush=True)
        else:
            print("SMOKE-FAIL %s: %s" % (name, detail), flush=True)
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
