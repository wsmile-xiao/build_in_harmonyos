#!/usr/bin/env python3
"""Real behavior test for the packaged isatapd binary (L0c test source).

isatapd registers 0 upstream test cases and its daemon runtime needs root +
a kernel ISATAP tunnel interface (unavailable on OHOS userland), so the
assertable surface is the installed binary's own option parser. Two behavior
assertions, matching the N_consumer figure in MANIFEST.yml/notes.md/PR body:
  [1/2] -h prints the FULL usage banner (Usage line + --name + --link +
        tunnel) -> binary is linked and its getopt parser is real, not a stub
  [2/2] an unknown long option exits non-zero with the 'unrecognized option'
        diagnostic -> argument validation actually runs
Any failed assertion exits non-zero, so conan's test() self.run() raises.
"""
import subprocess
import sys


def main():
    if len(sys.argv) < 3 or sys.argv[1] != "--binary":
        print("usage: test_smoke.py --binary <path-to-isatapd>")
        return 2
    binary = sys.argv[2]

    p = subprocess.run([binary, "-h"], capture_output=True, text=True)
    out = (p.stdout or "") + (p.stderr or "")
    need = ["Usage: isatapd", "--name", "--link", "tunnel"]
    missing = [t for t in need if t not in out]
    if missing:
        print("FAIL [1/2] usage banner missing %s (out=%r)" % (missing, out[:160]))
        return 1
    print("PASS [1/2]: isatapd -h emits full usage banner (parser functional)")

    p = subprocess.run([binary, "--definitely-not-an-option"],
                       capture_output=True, text=True)
    out2 = (p.stdout or "") + (p.stderr or "")
    if p.returncode == 0 or "unrecognized option" not in out2:
        print("FAIL [2/2] unknown option rc=%s out=%r" % (p.returncode, out2[:160]))
        return 1
    print("PASS [2/2]: isatapd rejects unknown option with diagnostic")

    print("SUMMARY: 2/2 behavior assertions passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
