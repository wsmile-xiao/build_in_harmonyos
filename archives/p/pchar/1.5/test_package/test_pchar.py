#!/usr/bin/env python3
"""Consumer smoke and offline replay tests for the installed pchar binary."""

import os
import re
import subprocess
import sys


def main():
    if len(sys.argv) != 2:
        raise AssertionError("expected the installed pchar executable path")
    executable = sys.argv[1]

    def run_installed(*args):
        return subprocess.run(
            [executable, *args],
            check=True,
            capture_output=True,
            text=True,
        )

    fixture = os.path.join(os.path.dirname(__file__), "fixtures", "replay_ipv4.txt")
    replay = run_installed("-r", fixture, "-n")
    if not re.search(r"Path length:\s+1 hops", replay.stdout):
        raise AssertionError("saved-trace replay did not report a one-hop path")

    version = run_installed("--version")
    version_output = version.stdout + version.stderr
    if "pchar 1.5" not in version_output:
        raise AssertionError("--version did not identify pchar 1.5")

    help_output = run_installed("--help")
    help_text = help_output.stdout + help_output.stderr
    if "Usage:" not in help_text:
        raise AssertionError("--help did not print usage")


if __name__ == "__main__":
    main()
