"""Smoke-test the installed command without requiring network privileges."""

import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_help.py PACKAGE_FOLDER")
    program = Path(sys.argv[1], "bin", "pwnat")
    if not program.is_file():
        raise SystemExit("missing packaged pwnat")
    result = subprocess.run(
        [str(program), "-h"], capture_output=True, text=True,
        check=False, timeout=10,
    )
    output = result.stdout + result.stderr
    if result.returncode != 1 or "usage:" not in output or "-s" not in output or "-c" not in output:
        raise SystemExit(f"pwnat help probe failed ({result.returncode}): {output}")
    print("PWNAT_CONSUMER_PASS: pwnat -h (expected exit 1)")


if __name__ == "__main__":
    main()
