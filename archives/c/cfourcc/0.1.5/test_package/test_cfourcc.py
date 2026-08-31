#!/usr/bin/env python3
"""Conan test_package for cfourcc — verifies the cfourcc binary exists AND runs.

R34 consumer check (no empty-shell): cfourcc is package_type = "application",
the verifiable artifact is the installed binary under <pkg>/bin/.
This test executes `cfourcc -h` and asserts the real version banner
("cfourcc 0.1.5") is printed — proving the binary is runnable, not just present.
"""
import os
import subprocess
import sys


def main():
    pkg = sys.argv[1]
    bin_dir = os.path.join(pkg, "bin")
    cfourcc_bin = os.path.join(bin_dir, "cfourcc")
    if not os.path.isfile(cfourcc_bin):
        print(f"FAIL: cfourcc binary not found: {cfourcc_bin}")
        return 1
    # R34: actually execute the binary. `-h` prints usage + version banner,
    # does not touch any AVI file, safe in sandbox.
    # NOTE: cfourcc returns exit code 15 (0x0f) when run with -h and no file
    # argument — that is the program's own design (source: "return 0x0f;"
    # after help when no valid input), NOT a crash. So assert on output, not rc.
    r = subprocess.run([cfourcc_bin, "-h"], capture_output=True, text=True)
    out = (r.stdout or "") + (r.stderr or "")
    if "cfourcc 0.1.5" not in out:
        print(f"FAIL: version banner 'cfourcc 0.1.5' not in -h output "
              f"(rc={r.returncode}):\n{out[:300]}", file=sys.stderr)
        return 1
    print(f"OK: cfourcc binary present + runnable, -h banner: "
          f"{out.strip().splitlines()[0]} (rc={r.returncode} expected 15)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
