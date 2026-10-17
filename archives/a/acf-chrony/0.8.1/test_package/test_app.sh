#!/bin/bash
# test_app.sh — substantive functional verification of the acf-chrony package.
# $1 = acf-chrony conan package folder
# Runs test_app.lua (controller→model dispatch chain) and test_model.lua
# (full MODEL layer functional tests) via the lua-runner built by
# conanfile.py build() against conan lua/5.4.8 (R34).
set -euo pipefail

PKG="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
LUA_RUNNER="$HERE/lua-runner"

if [ ! -x "$LUA_RUNNER" ]; then
  echo "FAIL: lua-runner not found (build() must compile it against conan lua)"
  exit 1
fi

# Lua module search path: test-harness shims (posix/subprocess/json/md5/acf.*)
# are in share/lua/5.4 next to the runner; the packaged app plugin modules are
# resolved by the test scripts via the package folder argument.
export LUA_PATH="$HERE/share/lua/5.4/?.lua;$HERE/share/lua/5.4/?/init.lua;;"

# Test 1: controller→model dispatch chain + menu/roles/layout
"$LUA_RUNNER" "$HERE/test_app.lua" "$PKG"
rc=$?
if [ $rc -ne 0 ]; then
  echo "FAIL: app plugin functional test rc=$rc"
  exit 1
fi

# Test 2: full MODEL layer functional tests (config parse/validate/write-back)
"$LUA_RUNNER" "$HERE/test_model.lua" "$PKG"
rc=$?
if [ $rc -ne 0 ]; then
  echo "FAIL: model functional test rc=$rc"
  exit 1
fi

echo "ALL TESTS PASSED"
exit 0
