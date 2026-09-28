#!/usr/bin/env python3
"""test_simh.py — consumer smoke test for the packaged SIMH emulator binaries.

For every emulator in the package bin/ directory this script:

  * confirms the binary is present and executable,
  * runs it (banner enabled) feeding `quit` on stdin (SIMH's SCP reads commands
    from stdin; `quit` maps to the EXIT handler and the process returns 0), and
  * asserts the SCP banner "<machine> simulator V3.8-1" was printed and the
    process exited cleanly (return code 0, no fatal signal, within the
    timeout).

Running the packaged bin/ (rather than the source tree) proves the installed
artifacts are complete and functional on the current platform.
"""
import os
import signal
import subprocess
import sys

BINS = [
    "altair", "altairz80", "eclipse", "gri", "h316", "hp2100", "i1401",
    "i1620", "i7094", "ibm1130", "id16", "id32", "lgp", "nova", "pdp1",
    "pdp10", "pdp11", "pdp15", "pdp4", "pdp7", "pdp8", "pdp9", "s3", "sds",
    "vax", "vax780",
]

BANNER = "simulator V3.8-1"


def check(bindir, name):
    path = os.path.join(bindir, name)
    if not os.path.isfile(path):
        print("FAIL: %s binary missing in package bin/" % name, file=sys.stderr)
        return False
    if not os.access(path, os.X_OK):
        print("FAIL: %s is not executable" % name, file=sys.stderr)
        return False
    try:
        result = subprocess.run(
            [path],
            input="quit\n",
            timeout=60,
            capture_output=True,
            text=True,
        )
    except subprocess.TimeoutExpired:
        print("FAIL: %s timed out (did not exit on quit)" % name, file=sys.stderr)
        return False
    except OSError as exc:
        print("FAIL: %s could not be executed: %s" % (name, exc), file=sys.stderr)
        return False

    if result.returncode < 0:
        sig = signal.Signals(-result.returncode).name
        print("FAIL: %s terminated by signal %s" % (name, sig), file=sys.stderr)
        return False
    if result.returncode != 0:
        print("FAIL: %s exited with %d" % (name, result.returncode), file=sys.stderr)
        return False
    output = (result.stdout or "") + (result.stderr or "")
    if BANNER not in output:
        print("FAIL: %s did not print banner %r (got %r)" % (name, BANNER, output[:200]),
              file=sys.stderr)
        return False
    return True


def main():
    if len(sys.argv) < 2:
        print("usage: test_simh.py <package-bin-dir>", file=sys.stderr)
        return 2
    bindir = sys.argv[1]
    passed = 0
    for name in BINS:
        if check(bindir, name):
            passed += 1
            print("OK: %s started, printed banner and exited cleanly" % name)
    print("SIMH consumer smoke test: %d/%d assertions passed" % (passed, len(BINS)))
    return 0 if passed == len(BINS) else 1


if __name__ == "__main__":
    sys.exit(main())
