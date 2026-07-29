#!/usr/bin/env bash
set -euo pipefail

extension="$1"
test -f "$extension"
bash -n "$extension"
grep -q "cmd_otp" "$extension"
echo "PASS pass-otp extension"
