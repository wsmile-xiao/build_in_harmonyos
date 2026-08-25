#!/usr/bin/env python3
"""Consumer tests for both installed DXX-Rebirth engines."""

import os
import subprocess
import sys


def check_help(executable):
    result = subprocess.run(
        [executable, "-help"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        timeout=20,
    )
    output = result.stdout.lower()
    if result.returncode != 0:
        raise RuntimeError(
            f"{os.path.basename(executable)} -help exited {result.returncode}: {result.stdout}"
        )
    if "help" not in output and "option" not in output and "rebirth" not in output:
        raise RuntimeError(
            f"{os.path.basename(executable)} produced unexpected help output: {result.stdout}"
        )


def main():
    bindir = sys.argv[1]
    for command in ("d1x-rebirth", "d2x-rebirth"):
        executable = os.path.join(bindir, command)
        if not os.path.isfile(executable):
            raise RuntimeError(f"missing installed command: {executable}")
        check_help(executable)
    print("validated d1x-rebirth and d2x-rebirth command interfaces")


if __name__ == "__main__":
    main()
