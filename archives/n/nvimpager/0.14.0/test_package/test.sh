#!/bin/bash
# nvimpager smoke test — tests -v and -h without requiring neovim

set -euo pipefail

echo "[test] Running nvimpager smoke tests..."

echo "[test] Test 1: nvimpager -v (version output)"
nvimpager -v

echo "[test] Test 2: nvimpager -h (help output)"
nvimpager -h

echo "[test] All smoke tests passed!"
