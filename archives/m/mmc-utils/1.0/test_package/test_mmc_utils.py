#!/usr/bin/env python3
"""Smoke test for the installed `mmc` binary.

mmc-utils has no `--version` flag: `mmc --version` is reported as an unknown
command and exits 1 (see mmc.c: unknown commands are handled by the same table).
The version is printed by `mmc help` as the final line (mmc.c help()), so the
smoke test asserts on `help` output instead.
"""
import subprocess
import sys

executable = sys.argv[1]
result = subprocess.run(
    [executable, "help"],
    check=False,
    capture_output=True,
    text=True,
)

output = result.stdout + result.stderr
assert result.returncode == 0, result
# Command dispatch is functional: the usage table is printed.
assert "Usage for command" in output, output
# The build carried the release version (GIT_VERSION passed by the recipe).
assert "1.0" in output, output

print("mmc-utils CLI smoke test: help table + version assertion passed")
