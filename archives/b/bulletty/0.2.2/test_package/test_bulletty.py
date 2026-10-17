#!/usr/bin/env python3
"""Real assertions against the packaged bulletty binary.

The binary is a TUI (terminal user interface) feed reader. A TUI cannot be
driven non-interactively, so the test exercises the deterministic CLI surface
(clap-derived commands and the hs directory reporting subcommand), which is
the executable portion of the packaged artifact on a headless runner.
"""

import subprocess
import sys


def run(binary, *args, timeout=30):
    proc = subprocess.run(
        [binary, *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def main():
    binary = sys.argv[1]
    failures = []

    # 1. --version must report the packaged version.
    rc, out = run(binary, "--version")
    if rc != 0:
        failures.append(f"--version rc={rc} out={out!r}")
    elif "0.2.2" not in out:
        failures.append(f"--version did not contain 0.2.2: {out!r}")

    # 2. --help must expose the TUI identity and the feed-manager subcommands.
    rc, out = run(binary, "--help")
    if rc != 0:
        failures.append(f"--help rc={rc} out={out!r}")
    else:
        for needle in ("Your TUI feed reader", "list", "add", "update", "delete", "import", "export"):
            if needle not in out:
                failures.append(f"--help missing {needle!r}")

    # 3. `dirs` (headless-safe) must print the bulletty library and log paths.
    rc, out = run(binary, "dirs")
    if rc != 0:
        failures.append(f"dirs rc={rc} out={out!r}")
    else:
        for needle in ("Library:", "Logs:"):
            if needle not in out:
                failures.append(f"dirs missing {needle!r}")

    if failures:
        print("ASSERTION FAILURES:", *failures, sep="\n  ")
        sys.exit(1)
    print("bulletty smoke: 3/3 assertions passed")
    sys.exit(0)


if __name__ == "__main__":
    main()