#!/usr/bin/env python3
"""bareos-client consumer test (L0c + R34: standalone test source executed
via self.run from conanfile.py test()).

bareos-fd (File Daemon) connects to a Bareos Director at runtime
(absent on OHOS — environment limitation, documented). Four real checks:
binary presence, executable bit, ELF identity, and actual `--version`
execution. Emits the HMBS_TEST_PACKAGE_RESULT evidence marker.

Usage: test_bareos_fd.py <package-folder>
"""
import json
import os
import subprocess
import sys


def check(name, func):
    try:
        detail = func()
    except AssertionError as exc:
        print("FAIL: %s: %s" % (name, exc))
        return False
    print("PASS: %s%s" % (name, (" (%s)" % detail) if detail else ""))
    return True


def main():
    if len(sys.argv) != 2:
        print("usage: %s <package-folder>" % sys.argv[0], file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "bareos-fd")

    results = []
    results.append(check("binary present",
                         lambda: _exists(exe)))
    results.append(check("executable bit",
                         lambda: _executable(exe)))
    results.append(check("ELF identity",
                         lambda: _is_elf(exe)))
    results.append(check("--version execution",
                         lambda: _run_version(exe)))

    discovered = len(results)
    passed_count = sum(1 for ok in results if ok)
    marker = {
        "executed": True,
        "passed": all(results),
        "command": "python3 test_bareos_fd.py <package>",
        "discovered": discovered,
        "passedCount": passed_count,
    }
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, separators=(",", ":")))
    return 0 if all(results) else 1


def _exists(exe):
    if not os.path.isfile(exe):
        raise AssertionError("missing: %s" % exe)
    return exe


def _executable(exe):
    if not os.access(exe, os.X_OK):
        raise AssertionError("not executable: %s" % exe)
    return "X_OK"


def _is_elf(exe):
    with open(exe, "rb") as blob:
        magic = blob.read(4)
    if magic != b"\x7fELF":
        raise AssertionError("not an ELF binary: %s" % exe)
    return "ELF aarch64" if _is_aarch64(exe) else "ELF"


def _is_aarch64(exe):
    with open(exe, "rb") as blob:
        header = blob.read(20)
    return len(header) == 20 and header[18:20] == b"\xb7\x00"


def _run_version(exe):
    try:
        proc = subprocess.run([exe, "--version"], capture_output=True,
                              text=True, timeout=30)
    except subprocess.TimeoutExpired:
        raise AssertionError("--version timed out after 30s")
    output = (proc.stdout + proc.stderr).strip()
    if proc.returncode != 0:
        raise AssertionError("--version rc=%d: %s"
                             % (proc.returncode, output[:200]))
    if not output:
        raise AssertionError("--version produced no output")
    first_line = output.splitlines()[0][:120]
    return first_line


if __name__ == "__main__":
    sys.exit(main())
