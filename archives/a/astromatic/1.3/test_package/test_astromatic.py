#!/usr/bin/env python3
"""astromatic metapackage consumer test (L0c + R34): smoke the 7 AstrOmatic
tool binaries required by the metapackage.

Each tools version/help flag follows its own recipes consumer test:
  missfits/psfex/swarp/ww  : --help prints SYNTAX usage (exit may be non-0)
  scamp                    : --version (exit 0)
  source-extractor (sex)   : --version (exit 0, prints SExtractor version)
  stiff                    : -v (exit 0, prints version)
"""
import shutil
import subprocess
import sys

TOOLS = [
    # (binary, flag, expected_text_lower, require_exit0)
    ("missfits", "--help", "syntax", False),
    ("psfex", "--help", "syntax", False),
    ("scamp", "--version", "scamp", True),
    ("sex", "--version", "2.28.2", True),
    ("stiff", "-v", "version", True),
    ("swarp", "--help", "syntax", False),
    ("ww", "--help", "syntax", False),
]


def main() -> int:
    failed = []
    for bin_name, flag, expected, require_rc0 in TOOLS:
        exe = shutil.which(bin_name)
        if not exe:
            failed.append(f"{bin_name}: not in PATH")
            continue
        try:
            r = subprocess.run([exe, flag], capture_output=True, text=True,
                               timeout=90)
        except subprocess.TimeoutExpired:
            failed.append(f"{bin_name} {flag}: timeout")
            continue
        combined = (r.stdout + r.stderr).lower()
        if require_rc0 and r.returncode != 0:
            failed.append(f"{bin_name} {flag}: rc={r.returncode}")
            continue
        if expected not in combined:
            failed.append(f"{bin_name} {flag}: expected {expected!r} not in "
                          f"output: {combined[:120]}")
            continue
        print(f"OK: {bin_name} {flag}")
    if failed:
        print("FAILED: " + "; ".join(failed), file=sys.stderr)
        return 1
    print("astromatic smoke: all 7 AstrOmatic binaries OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
