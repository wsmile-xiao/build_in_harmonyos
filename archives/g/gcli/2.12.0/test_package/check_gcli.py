#!/usr/bin/env python3
"""Non-network smoke checks for the packaged gcli executable."""
import os
import subprocess
import sys


if len(sys.argv) != 2:
    raise SystemExit("usage: check_gcli.py <gcli-bin>")

gcli = sys.argv[1]

def require(condition, message):
    if not condition:
        raise SystemExit(message)


require(os.path.isfile(gcli), f"missing gcli executable: {gcli}")
require(os.access(gcli, os.X_OK), f"gcli is not executable: {gcli}")

default_prefix = os.environ.get("DEFAULT_PREFIX", "/storage/Users/currentUser/usr/local")
env = dict(os.environ)
env["LD_LIBRARY_PATH"] = os.pathsep.join(
    path for path in [os.path.join(default_prefix, "lib"), env.get("LD_LIBRARY_PATH", "")] if path
)

version = subprocess.run([gcli, "version"], check=True, text=True, capture_output=True, timeout=15, env=env)
version_output = version.stdout + version.stderr
require("gcli 2.12.0" in version_output, version_output)
require("Using libcurl/" in version_output, version_output)
require("Using vendored pdjson library" in version_output, version_output)

usage = subprocess.run([gcli], check=False, text=True, capture_output=True, timeout=15, env=env)
usage_output = usage.stdout + usage.stderr
require(usage.returncode != 0, f"expected non-zero usage exit, got {usage.returncode}")
require("usage: gcli" in usage_output, usage_output)
