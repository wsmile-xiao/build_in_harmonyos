"""Deterministic consumer checks for the installed ud binary."""

import subprocess
import sys


binary = sys.argv[1]


def run(argument):
    return subprocess.run([binary, argument], text=True, capture_output=True,
                          timeout=10)


cases = (
    ("--version", "Version: 1.1.0"),
    ("0", "1970-01-01"),
    ("-1", "1969-12-31"),
    ("20000", "2024-10-04"),
    ("2024-10-04", "20000"),
    ("04.10.2024", "20000"),
    ("10/04/2024", "20000"),
)
for argument, expected in cases:
    result = run(argument)
    assert result.returncode == 0, (argument, result.stderr)
    assert result.stdout.strip() == expected, (argument, result.stdout)

help_result = run("--help")
assert help_result.returncode == 0, help_result.stderr
assert "Usage:" in help_result.stdout, help_result.stdout

invalid_result = run("not-a-date")
assert invalid_result.returncode != 0, invalid_result.stdout
assert "Invalid date" in invalid_result.stderr, invalid_result.stderr

print("ud installed-package consumer checks: 9/9 PASS")
