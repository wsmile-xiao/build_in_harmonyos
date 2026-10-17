#!/usr/bin/env bash
# test_package/test.sh — nsuds binary functional smoke test (R34 / PF3).
# Exercises the non-interactive CLI paths of the packaged game binary and
# asserts their real output content.
set -euo pipefail

NS="${1:?usage: test.sh <path-to-nsuds-binary>}"

if [ ! -x "$NS" ]; then
  echo "[FAIL] nsuds binary not found/executable: $NS" >&2
  exit 1
fi

"$NS" --version | grep -q "nsuds version 0.7B"
"$NS" -v           | grep -q "0.7B"
"$NS" --help       | grep -qi "Usage: nsuds"
"$NS" -h           | grep -qi "Usage: nsuds"
# --help lists the real long options of this build
"$NS" --help       | grep -qi "\-\-no-color"

echo "[ok] nsuds version/help non-interactive CLI verified ($NS)"
