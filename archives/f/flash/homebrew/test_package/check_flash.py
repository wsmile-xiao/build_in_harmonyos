#!/usr/bin/env python3
"""Non-destructive smoke checks for the packaged flash script."""
import os
import subprocess
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: check_flash.py <flash-bin>")

flash = sys.argv[1]

assert os.path.isfile(flash), flash
assert os.access(flash, os.X_OK), flash

version = subprocess.run([flash, "--version"], check=True, text=True, capture_output=True)
assert version.stdout.strip() == "2.7.2", version.stdout

help_result = subprocess.run([flash, "--help"], check=False, text=True, capture_output=True)
assert help_result.returncode == 1, help_result.returncode
assert "Flash a local or remote Raspberry Pi SD card image." in help_result.stdout
