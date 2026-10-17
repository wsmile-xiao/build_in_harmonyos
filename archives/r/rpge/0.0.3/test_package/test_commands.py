#!/usr/bin/env python3
"""Run RPGE's non-graphical command paths on the target HarmonyOS PC."""

import subprocess
import sys


def main():
    executable = sys.argv[1]
    help_result = subprocess.run(
        [executable, "--help"], text=True, capture_output=True, check=True
    )
    assert "Usage:" in help_result.stdout, help_result.stdout
    version_result = subprocess.run(
        [executable, "--version"], text=True, capture_output=True, check=True
    )
    assert version_result.stdout.startswith("GNU RPGE 0.0.1\n"), version_result.stdout
    print("RPGE help/version consumer checks passed (2/2)")


if __name__ == "__main__":
    main()
