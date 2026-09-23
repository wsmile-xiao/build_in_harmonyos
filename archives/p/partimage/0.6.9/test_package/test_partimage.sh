#!/bin/sh
set -euo pipefail 2>/dev/null || set -eu
# test_partimage.sh — partimage smoke test
# Runs partimage with --version to verify the binary is functional
partimage --version 2>&1 | head -5
