#!/bin/sh
# acf-unbound 0.1.0 consumer test script (POSIX sh)
# Usage: sh test_acf_unbound.sh <package_folder>
# Substantive checks (R34): ACF app artifacts present under
# usr/share/acf/app/unbound/ with real controller/model/menu/roles content.
#
# Note: this app is pure Lua/data (no ELF binary), so the test validates
# content markers that the acf-core framework loads at runtime.

set -eu

pkg="$1"
fail=0

appdir="$pkg/usr/share/acf/app/unbound"

check_file() {
    rel="$1"
    if [ ! -e "$appdir/$rel" ]; then
        echo "[FAIL] missing artifact: $rel"
        fail=1
        return
    fi
    echo "[OK] $rel"
}

check_grep() {
    rel="$1"
    pattern="$2"
    if grep -qE "$pattern" "$appdir/$rel"; then
        echo "[OK] $rel contains: $pattern"
    else
        echo "[FAIL] $rel missing marker: $pattern"
        fail=1
    fi
}

check_fixed() {
    rel="$1"
    marker="$2"
    if grep -qF "$marker" "$appdir/$rel"; then
        echo "[OK] $rel contains: $marker"
    else
        echo "[FAIL] $rel missing marker: $marker"
        fail=1
    fi
}

check_file unbound-controller.lua
check_file unbound-model.lua
check_file unbound.menu
check_file unbound.roles

# Controller must expose the ACF default_action hook (real app, not stub)
check_grep unbound-controller.lua 'default_action *='

# Model must load ACF framework libraries
check_fixed unbound-model.lua 'require("acf.fs")'

# Menu must reference the unbound app group/actions
check_grep unbound.menu 'Unbound'

# Roles must declare the unbound permission set
check_grep unbound.roles 'unbound:status'

if [ "$fail" -ne 0 ]; then
    echo "[FAIL] acf-unbound test failed"
    exit 1
fi
echo "[PASS] acf-unbound artifacts verified"
