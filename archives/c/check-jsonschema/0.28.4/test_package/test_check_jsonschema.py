#!/usr/bin/env python3
"""test_check_jsonschema.py — check-jsonschema test_package validation script.

CI L0c requires a test source file (non conanfile.py) in test_package/.
check-jsonschema is a pure Python CLI tool, this script executes
`check-jsonschema --version` to verify the package is installed and functional
(R34: test_package must execute the tested package's binary).
The actual test entry point is test_package/conanfile.py test() method.
"""

import subprocess
import sys


def main():
    """Verify check-jsonschema is executable and --version output is correct."""
    result = subprocess.run(
        [sys.executable, "-m", "check_jsonschema", "--version"],
        capture_output=True, text=True, timeout=30,
    )
    if result.returncode != 0 or "0.28.4" not in (result.stdout + result.stderr):
        print(
            f"FAIL: check-jsonschema --version returned {result.returncode}: "
            f"{result.stdout!r} {result.stderr!r}",
            file=sys.stderr,
        )
        return 1
    print(f"OK: {(result.stdout + result.stderr).strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
