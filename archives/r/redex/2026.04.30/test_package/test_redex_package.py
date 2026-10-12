#!/usr/bin/env python3
"""Exercise the installed native optimizer and Python driver."""

import pathlib
import re
import subprocess
import sys


def run_checked(command):
    completed = subprocess.run(
        command,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"command failed ({completed.returncode}): {command}\n{completed.stdout}"
        )
    return completed.stdout


def main():
    binary = pathlib.Path(sys.argv[1])
    driver = pathlib.Path(sys.argv[2])
    if not binary.is_file() or not driver.is_file():
        raise RuntimeError("Redex package is missing redex-all or redex.py")

    passes_output = run_checked([str(binary), "--show-passes"])
    match = re.search(r"Registered passes:\s*(\d+)", passes_output)
    if not match or int(match.group(1)) <= 0:
        raise RuntimeError(f"invalid registered-pass output:\n{passes_output}")

    help_output = run_checked([sys.executable, str(driver), "--help"])
    if "usage:" not in help_output.lower() or "--redex-binary" not in help_output:
        raise RuntimeError(f"invalid redex.py help output:\n{help_output}")

    print(f"REDEX_REGISTERED_PASSES={match.group(1)}")
    print("REDEX_PACKAGE_TEST=PASS")


if __name__ == "__main__":
    main()
