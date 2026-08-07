#!/bin/bash
# test_acf_core.sh — substantive functional verification of the acf-core package.
# $1 = acf-core conan package folder
set -u

PKG="$1"
HERE="$(cd "$(dirname "$0")" && pwd)"
LUA_RUNNER="$HERE/lua-runner"
BASE="$PKG/share"
HARN="$HERE/share/lua/5.4"

if [ ! -x "$LUA_RUNNER" ]; then
  echo "FAIL: lua-runner not found (build() must compile it against conan lua)"
  exit 1
fi

# Lua module search path: packaged acf framework + test-harness modules
export LUA_PATH="$BASE/lua/5.4/?.lua;$BASE/lua/5.4/?/init.lua;$BASE/acf/lib/?.lua;$HARN/?.lua;$HARN/?/init.lua;;"

# Home-based ACF config so read_config() works without touching read-only /etc
CFG_HOME="$HERE/test-home"
mkdir -p "$CFG_HOME/.acf"
cat > "$CFG_HOME/.acf/acf.conf" <<EOF
appdir=$BASE/acf/app/
libdir=$BASE/acf/lib/
wwwdir=$BASE/acf/www/
sessiondir=$HERE/sessions/
skindir=/skins/,/userskins/
EOF
mkdir -p "$HERE/sessions"

# ── Framework functional test (loads acf.mvc + dispatches welcome/read) ──
"$LUA_RUNNER" "$HERE/test_framework.lua" "$PKG" "$CFG_HOME"
rc=$?
if [ $rc -ne 0 ]; then
  echo "FAIL: framework functional test rc=$rc"
  exit 1
fi

# ── CLI tool behavior ──
if [ -f "$PKG/bin/acfpasswd" ]; then
  OUT=$(bash "$PKG/bin/acfpasswd" 2>&1); rc=$?
  echo "$OUT" | grep -q "usage: acfpasswd" || { echo "FAIL: acfpasswd usage"; exit 1; }
  echo "[OK] acfpasswd prints usage (exit $rc)"
fi

if [ -f "$PKG/bin/acf-cli" ]; then
  OUT=$("$LUA_RUNNER" "$PKG/bin/acf-cli" 2>&1); rc=$?
  echo "$OUT" | grep -q "ACF Client interface" || { echo "FAIL: acf-cli help"; exit 1; }
  echo "[OK] acf-cli prints usage"
fi

echo "ALL TESTS PASSED"
exit 0
