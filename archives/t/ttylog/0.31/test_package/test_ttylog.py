"""Functional checks against the packaged ttylog executable."""

import subprocess
import sys

binary, runner = sys.argv[1:3]
command = ([runner] if runner else []) + [binary]
for name, args, expected in (
    ("no arguments", [], "no params."),
    ("help", ["--help"], "Usage:"),
    ("version", ["--version"], "ttylog version 0.31.0"),
    ("invalid device", ["--device", "/not-a-ttylog-device"], "invalid device"),
):
    proc = subprocess.run(command + args, capture_output=True, text=True, timeout=10)
    assert proc.returncode == 0 and expected in proc.stdout, (
        name, proc.returncode, proc.stdout, proc.stderr
    )
    print(f"PASS: {name}")
