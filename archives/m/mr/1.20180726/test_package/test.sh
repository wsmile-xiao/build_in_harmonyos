#!/usr/bin/env bash
# test_package/test.sh — smoke test for mr (myrepos) CLI
set -euo pipefail

echo "[test] mr help"
if mr help | grep -i "mr" > /dev/null; then
    echo "mr help: OK"
else
    echo "mr help: FAILED" >&2
    exit 1
fi

echo "[test] mr register (core functionality)"
if ! command -v git >/dev/null 2>&1; then
    echo "mr register: SKIP (git not available in this environment)"
else
    # Use temporary HOME to isolate ~/.mrconfig and avoid polluting CI environment
    TMPHOME=$(mktemp -d)
    TMPDIR=$(mktemp -d)
    cd "$TMPDIR"
    # Create a fake git repo to register
    git init test-repo 2>/dev/null
    cd test-repo
    # Run mr register with isolated HOME to avoid polluting ~/.mrconfig
    if HOME="$TMPHOME" mr register 2>&1; then
        # Verify .mrconfig was created in the temporary HOME
        if [ -f "$TMPHOME/.mrconfig" ]; then
            echo "mr register: OK (mrconfig created)"
        else
            echo "mr register: FAILED (mrconfig not found after mr register)" >&2
            exit 1
        fi
    else
        echo "mr register: FAILED (mr register exited non-zero)" >&2
        exit 1
    fi
    cd /
    rm -rf "$TMPDIR" "$TMPHOME"
fi

echo "[test] webcheckout exists"
if command -v webcheckout >/dev/null 2>&1; then
    echo "webcheckout found: OK"
else
    echo "webcheckout not found: FAILED" >&2
    exit 1
fi

echo "[test] mr smoke test: PASS"
