#!/bin/bash
# Smoke test for xdg-dbus-proxy binary
# This file satisfies CI L0c requirement (test source file in test_package/)
# The actual test logic runs in conanfile.py test() via self.run()
set -e

BIN_PATH="${1:-xdg-dbus-proxy}"

# --version: should print version and exit 0
"$BIN_PATH" --version

# --help: should print usage and exit 0
"$BIN_PATH" --help

echo "All smoke tests passed"
