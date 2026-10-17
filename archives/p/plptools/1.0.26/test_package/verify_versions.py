"""Run every packaged core command without requiring Psion hardware."""

import subprocess
import sys
from pathlib import Path


COMMANDS = ("ncpd", "plpftp", "plpprintd", "sisinstall")


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_versions.py PACKAGE_FOLDER")
    package = Path(sys.argv[1])
    for name in COMMANDS:
        program = package / "bin" / name
        if not program.is_file():
            raise SystemExit(f"missing packaged command {name}")
        result = subprocess.run(
            [str(program), "--version"], capture_output=True,
            text=True, check=False, timeout=10,
        )
        version = (result.stdout + result.stderr).strip()
        if result.returncode != 0:
            raise SystemExit(f"{name} version probe failed ({result.returncode}): {version}")
        print(f"PLPTOOLS_CONSUMER_PASS: {name} --version")


if __name__ == "__main__":
    main()
