"""Ensure all four installed rlpr commands execute and report their version."""

import os
import subprocess
import sys
from pathlib import Path


COMMANDS = ("rlpr", "rlpq", "rlprm", "rlprd")


def main():
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_versions.py PACKAGE_FOLDER")
    package = Path(sys.argv[1])
    # Upstream validates the default printer before parsing -V.  The version
    # handler exits before any connection, so provide an inert loopback target.
    environment = dict(os.environ, PRINTER="lp@127.0.0.1")
    for name in COMMANDS:
        program = package / "bin" / name
        if not program.is_file():
            raise SystemExit(f"missing packaged command {name}")
        result = subprocess.run(
            [str(program), "-V"], capture_output=True, text=True,
            check=False, timeout=10, env=environment,
        )
        output = result.stdout + result.stderr
        if result.returncode != 0 or "version 2.06" not in output:
            raise SystemExit(f"{name} version probe failed ({result.returncode}): {output}")
        print(f"RLPR_CONSUMER_PASS: {name} -V")


if __name__ == "__main__":
    main()
