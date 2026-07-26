#!/usr/bin/env bash
# test_package/test.sh — smoke test for prettyping CLI
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MOCK_PING="$SCRIPT_DIR/mock-ping.sh"

echo "[test] prettyping help"
help_output="$(prettyping --help)"
[[ "$help_output" == *"Usage:"* ]]
[[ "$help_output" == *"recentstats"* ]]

echo "[test] prettyping missing parameters"
set +e
missing_output="$(prettyping --nocolor --nounicode --noterminal 2>&1)"
missing_status=$?
set -e
if [ "$missing_status" -eq 0 ]; then
    echo "[error] prettyping unexpectedly accepted missing ping target"
    exit 1
fi
[[ "$missing_output" == *"Missing parameters"* ]]

echo "[test] prettyping mock ping output"
mock_output="$(PATH="$SCRIPT_DIR:$PATH" prettyping \
    --nocolor \
    --nounicode \
    --noterminal \
    --nolegend \
    --last 2 \
    --pingbin "$MOCK_PING" \
    example.test)"

[[ "$mock_output" == *"lost;"* ]]
[[ "$mock_output" == *"_"* ]]

echo "[test] prettyping smoke test: PASS"
