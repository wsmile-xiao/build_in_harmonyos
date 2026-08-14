#!/usr/bin/env bash
# test_package/test.sh — nsnake binary smoke test
set -euo pipefail

nsnake --version
echo "[ok] nsnake binary smoke test passed"