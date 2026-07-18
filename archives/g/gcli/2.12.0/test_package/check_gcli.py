#!/usr/bin/env python3
"""Non-network smoke checks for the packaged gcli executable."""
import os
import subprocess
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: check_gcli.py <gcli-bin>")

gcli = sys.argv[1]

assert os.path.isfile(gcli), gcli
assert os.access(gcli, os.X_OK), gcli

version = subprocess.run([gcli, "version"], check=True, text=True, capture_output=True, timeout=15)
version_output = version.stdout + version.stderr
assert "gcli 2.12.0" in version_output, version_output
assert "Using libcurl/" in version_output, version_output
assert "Using vendored pdjson library" in version_output, version_output

usage = subprocess.run([gcli], check=False, text=True, capture_output=True, timeout=15)
usage_output = usage.stdout + usage.stderr
assert usage.returncode != 0, usage.returncode
assert "usage: gcli" in usage_output, usage_output
