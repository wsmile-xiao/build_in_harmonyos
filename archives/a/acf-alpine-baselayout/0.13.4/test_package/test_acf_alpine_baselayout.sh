#!/bin/bash
# test_acf_alpine_baselayout.sh — substantive verification (R34) of the
# packaged acf-alpine-baselayout pure-Lua ACF application module.
#   $1 = acf-alpine-baselayout conan package folder
#   $2 = test build folder (contains lua-runner + test_syntax.lua)
set -u

PKG="$1"
TESTDIR="$2"
RUNNER="$TESTDIR/lua-runner"
APPDIR="$PKG/usr/share/acf/app/alpine-baselayout"

PASS=0
FAIL=0
ok() { echo "  [OK] $1"; PASS=$((PASS+1)); }
no() { echo "  [FAIL] $1"; FAIL=$((FAIL+1)); }

echo "=== acf-alpine-baselayout consumer test ==="
echo "  package root: $PKG"
echo "  app dir: $APPDIR"

if [ ! -d "$APPDIR" ]; then
  no "packaged app dir exists: $APPDIR"
  echo "  Result: PASS=$PASS FAIL=$FAIL"
  exit 1
else
  ok "packaged app dir exists"
fi

# 1) Required controllers (10 app modules)
for c in alpineversion cron health hostname interfaces logfiles modules password rc syslog; do
  f="$APPDIR/$c-controller.lua"
  [ -f "$f" ] && ok "controller: $c-controller.lua" || no "controller missing: $c-controller.lua"
done

# 2) Required models
for m in alpineversion cron health hostname interfaces logfiles modules password rc syslog; do
  f="$APPDIR/$m-model.lua"
  [ -f "$f" ] && ok "model: $m-model.lua" || no "model missing: $m-model.lua"
done

# 3) Menu definitions
for m in cron health interfaces logfiles modules rc syslog; do
  f="$APPDIR/$m.menu"
  [ -f "$f" ] && ok "menu: $m.menu" || no "menu missing: $m.menu"
done

# 4) Roles file + content (GUEST/USER/EDITOR/EXPERT/ADMIN)
if [ -f "$APPDIR/alpine-baselayout.roles" ]; then
  ok "roles file exists"
  for role in GUEST USER EDITOR EXPERT ADMIN; do
    grep -q "^$role=" "$APPDIR/alpine-baselayout.roles" && ok "roles define $role" || no "roles missing $role"
  done
else
  no "roles file missing"
fi

# 5) Sample .lsp views (regular files + symlinked framework views)
for v in health-system-html.lsp interfaces-read-html.lsp logfiles-status-html.lsp \
         rc-status-html.lsp syslog-config-html.lsp cron-listjobs-html.lsp; do
  [ -f "$APPDIR/$v" ] && ok "view: $v" || no "view missing: $v"
done
for v in cron-status-html.lsp syslog-status-html.lsp interfaces-create-html.lsp; do
  [ -L "$APPDIR/$v" ] && ok "symlinked view: $v" || no "symlinked view missing: $v"
done

# 6) No lib/bin artifacts (pure app module)
[ -d "$PKG/usr/lib" ] && no "unexpected usr/lib dir" || ok "no usr/lib artifacts"
[ -d "$PKG/usr/bin" ] && no "unexpected usr/bin dir" || ok "no usr/bin artifacts"

# 7) Lua 5.4 syntax-load of every packaged .lua (real runtime from conan lua)
if [ -x "$RUNNER" ]; then
  if "$RUNNER" "$TESTDIR/test_syntax.lua" "$APPDIR" > "$TESTDIR/syntax.log" 2>&1; then
    ok "all packaged .lua files pass Lua 5.4 syntax load"
  else
    no "Lua syntax check failed (see syntax.log)"
    cat "$TESTDIR/syntax.log"
  fi
else
  no "lua-runner not found in $TESTDIR"
fi

echo ""
echo "=== Result: PASS=$PASS FAIL=$FAIL ==="
[ "$FAIL" -gt 0 ] && exit 1
exit 0
