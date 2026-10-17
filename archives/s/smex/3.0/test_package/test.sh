#!/usr/bin/env bash
# test_package/test.sh — verify smex.el installation
# Usage: bash test.sh <package_folder>
#
# smex is a pure Emacs Lisp package with no binary to execute.
# This script verifies the actual package content:
#   1. smex.el file exists in share/emacs/site-lisp/
#   2. smex.el declares "Version: 3.0"
#   3. smex.el defines the (defun smex ...) entry function
set -euo pipefail

# Bash syntax self-check (project convention)
bash -n "$0"

PKG_DIR="${1:-}"
if [ -z "$PKG_DIR" ]; then
    echo "FAIL: package folder argument required" >&2
    exit 1
fi

SMEX_EL="${PKG_DIR}/share/emacs/site-lisp/smex.el"

# Assertion 1: smex.el must exist
if [ ! -f "$SMEX_EL" ]; then
    echo "FAIL: smex.el not found at ${SMEX_EL}" >&2
    exit 1
fi
echo "PASS: smex.el exists at ${SMEX_EL}"

# Assertion 2: smex.el must declare Version: 3.0
if ! grep -q "Version: 3.0" "$SMEX_EL"; then
    echo "FAIL: smex.el does not contain 'Version: 3.0'" >&2
    exit 1
fi
echo "PASS: version string 'Version: 3.0' found"

# Assertion 3: smex.el must define the smex() entry function
if ! grep -q "(defun smex " "$SMEX_EL"; then
    echo "FAIL: smex.el does not define (defun smex ...)" >&2
    exit 1
fi
echo "PASS: smex function definition found"

echo "All assertions passed"
