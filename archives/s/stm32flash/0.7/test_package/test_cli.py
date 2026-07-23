#!/usr/bin/env python3
"""Functional checks for the installed stm32flash executable."""
import subprocess
import sys


def main() -> int:
    binary = sys.argv[1]

    help_result = subprocess.run(
        [binary, "-h"], capture_output=True, text=True, check=False
    )
    help_output = help_result.stdout + help_result.stderr
    if "Usage:" not in help_output or "stm32flash" not in help_output:
        raise RuntimeError("stm32flash help output is incomplete")

    port_result = subprocess.run(
        [binary, "-k", "/dev/codex-no-such-stm32"],
        capture_output=True,
        text=True,
        check=False,
    )
    port_output = port_result.stdout + port_result.stderr
    if port_result.returncode == 0 or "Failed to open port" not in port_output:
        raise RuntimeError("stm32flash did not exercise the serial-port error path")

    print("stm32flash CLI and serial-port handling validated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
