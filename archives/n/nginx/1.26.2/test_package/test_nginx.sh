#!/bin/sh
set -euo pipefail
# Smoke test for nginx binary
# Runs nginx -V and checks version output
NGINX_BIN="${1:-nginx}"
output=$("$NGINX_BIN" -V 2>&1)
if echo "$output" | grep -q "nginx/1.26.2"; then
    echo "PASS: nginx version correct"
    exit 0
else
    echo "FAIL: unexpected nginx output: $output"
    exit 1
fi
