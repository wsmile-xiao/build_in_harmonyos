#!/usr/bin/env python3
"""Smoke test for the packaged cxxtestgen entry point.

Executed from test_package/conanfile.py via self.run (CI L0d), so this
file also satisfies the L0c test-source requirement (R34: execute the
packaged binary).

Usage:
    python3 cxxtest_smoke.py <cxxtestgen-path-or-name> [python-exe]

Single smoke case, fail-fast:
  1. `<cxxtestgen> --version` exits 0 and prints "CxxTest version"
     (upstream cxxtestgen.py printVersion writes
     "This is CxxTest version %s." then sys.exit(0)).
  2. `<cxxtestgen> --help` exits 0 and prints optparse "Usage" text
     (OptionParser("cxxtestgen [options] [<filename> ...]")).

Both prove the packaged generator survived packaging (files,
permissions, python/ module layout) and remains executable.
"""

import os
import shutil
import subprocess
import sys


def _run(cmd, timeout=120):
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, timeout=timeout)
    except Exception as exc:
        print("smoke FAILED to launch %s: %s" % (" ".join(cmd), exc))
        return None
    return proc


def _check(cmd, must_contain):
    print("smoke: running: %s" % " ".join(cmd))
    proc = _run(cmd)
    if proc is None:
        return False
    out = (proc.stdout or "") + (proc.stderr or "")
    print(out[-2000:])
    if proc.returncode != 0:
        print("smoke FAILED: exit code %d" % proc.returncode)
        return False
    if not out.strip():
        print("smoke FAILED: empty output")
        return False
    lowered = out.lower()
    for token in must_contain:
        if token not in lowered:
            print("smoke FAILED: output lacks %r" % token)
            return False
    return True


def _resolve_python(candidate):
    # The caller may pass bare "python3", which is missing from the default
    # PATH on CI workers inside this nested subprocess (self.run's conanrun
    # env is not inherited here). Resolve to an absolute interpreter that
    # is guaranteed to exist: existing file wins, then PATH lookup, then
    # the interpreter running this script.
    if candidate and os.path.isfile(candidate):
        return candidate
    if candidate:
        found = shutil.which(candidate)
        if found:
            return found
    if sys.executable and os.path.isfile(sys.executable):
        return sys.executable
    return candidate


def main(argv):
    if len(argv) < 2:
        print("usage: cxxtest_smoke.py <cxxtestgen> [python]")
        return 2
    gen = argv[1]
    python = _resolve_python(argv[2] if len(argv) > 2 else sys.executable)
    if os.path.isfile(gen):
        base = [python, gen]
    else:
        # Even a PATH-resolved cxxtestgen is a python script without exec
        # guarantee on OHOS/CI, so always launch it via the interpreter.
        # Resolve the script through PATH when only a name was given.
        gen_path = shutil.which(gen) or gen
        base = [python, gen_path]
    if not _check(base + ["--version"], ["cxxtest version"]):
        return 1
    if not _check(base + ["--help"], ["usage"]):
        return 1
    print("cxxtestgen smoke check passed")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
