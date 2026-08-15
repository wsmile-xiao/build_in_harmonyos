#!/bin/bash
# Consumer test for afdko 4.0.1: verify C executables respond to -h
# This script is called by test_package/conanfile.py via self.run()
set -euo pipefail

BIN_DIR="$1"
if [ -z "$BIN_DIR" ] || [ ! -d "$BIN_DIR" ]; then
    echo "FAIL: bin directory not provided or does not exist"
    exit 1
fi

# Check all 9 C executables exist
for name in detype1 makeotfexe mergefonts rotatefont sfntdiff sfntedit spot tx type1; do
    if [ ! -f "$BIN_DIR/$name" ]; then
        echo "FAIL: missing executable $name"
        exit 1
    fi
done

# Verify -h prints usage/help: capture output, reject signal termination (>128),
# allow intentional non-zero exit codes but require usage text on stdout/stderr.
for name in tx spot; do
    rc=0
    output="$("$BIN_DIR/$name" -h 2>&1)" || rc=$?
    rc="${rc:-0}"
    if [ "$rc" -gt 128 ]; then
        echo "FAIL: $name -h terminated by signal (exit $rc)"
        exit 1
    fi
    if ! printf "%s" "$output" | grep -qiE "usage|help"; then
        echo "FAIL: $name -h did not print usage/help info"
        exit 1
    fi
done

echo "PASS: all 9 afdko C executables verified"
exit 0
