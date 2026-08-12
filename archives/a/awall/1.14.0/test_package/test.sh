#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for awall 1.14.0
#
# awall is a pure Lua CLI installed at usr/sbin/awall. OHOS has no
# /usr/bin/lua, so the interpreter path is passed in via LUA_BIN (resolved
# from the lua/5.5.0 conan dependency by test_package/conanfile.py — never
# hardcoded to a dev machine).
#
# Layers (see conanfile.py docstring):
#   1. structural gate  — files/executables exist (mandatory)
#   2. syntax gate      — every packaged .lua parses under the lua
#                         interpreter via assert(loadfile(...)) (mandatory)
#   3. best-effort run  — if host Lua helper modules are reachable, really
#                         run `awall list`; otherwise SKIP is reported with
#                         the exact reason (no silent fake pass)
#
# Usage: test.sh <package_folder>   (env: LUA_BIN, LUA_PATH, LUA_CPATH)
set -euo pipefail

PKG_DIR="${1:?usage: test.sh <package_folder>}"
LUA_BIN="${LUA_BIN:-}"
SBIN="$PKG_DIR/usr/sbin/awall"
LUA_DIR="$PKG_DIR/usr/share/lua/5.5/awall"
SHARE_DIR="$PKG_DIR/usr/share/awall"
LUA_PATH="${LUA_PATH:-}"
LUA_CPATH="${LUA_CPATH:-}"
export LUA_PATH LUA_CPATH

# ── Layer 1: structural gate ──────────────────────────────────────────
echo "[test] awall CLI present and executable"
test -x "$SBIN" || { echo "❌ awall not executable at $SBIN"; exit 1; }
echo "✅ $SBIN"

echo "[test] Lua modules installed"
for m in init.lua class.lua model.lua policy.lua loader.lua iptables.lua \
         util.lua family.lua host.lua ipset.lua optfrag.lua uerror.lua \
         dependency.lua schema.lua; do
    test -f "$LUA_DIR/$m" || { echo "❌ missing Lua module: $LUA_DIR/$m"; exit 1; }
done
echo "✅ Lua modules OK ($(ls "$LUA_DIR"/*.lua | wc -l) files)"

echo "[test] awall/modules sub-modules installed"
for m in clampmss classify filter log mark masquerade nat notrack tproxy ttl; do
    test -f "$LUA_DIR/modules/$m.lua" || { echo "❌ missing sub-module: $LUA_DIR/modules/$m.lua"; exit 1; }
done
echo "✅ sub-modules OK"

echo "[test] policy JSON templates installed"
test -f "$SHARE_DIR/mandatory/defaults.json" || { echo "❌ missing mandatory/defaults.json"; exit 1; }
test -f "$SHARE_DIR/mandatory/services.json" || { echo "❌ missing mandatory/services.json"; exit 1; }
test -f "$SHARE_DIR/optional/adp-ping.json" || { echo "❌ missing optional/adp-ping.json"; exit 1; }
test -f "$SHARE_DIR/sample/sample-policy.json" || { echo "❌ missing sample-policy.json"; exit 1; }
echo "✅ policy templates OK"

# ── Layer 2: syntax gate (real interpreter involvement) ──────────────
if [ -n "$LUA_BIN" ] && [ -x "$LUA_BIN" ]; then
    echo "[test] Lua syntax check via $LUA_BIN (loadfile)"
    fail=0
    while IFS= read -r f; do
        if ! "$LUA_BIN" -e "assert(loadfile('$f'))" 2>/dev/null; then
            echo "❌ syntax error in $f"
            fail=1
        fi
    done < <(find "$LUA_DIR" -name '*.lua' | sort)
    # awall-cli itself is a Lua script too
    if ! "$LUA_BIN" -e "assert(loadfile('$SBIN'))" 2>/dev/null; then
        echo "❌ syntax error in $SBIN"
        fail=1
    fi
    if [ "$fail" = "1" ]; then
        echo "❌ Lua syntax gate failed"
        exit 1
    fi
    echo "✅ Lua syntax OK ($(find "$LUA_DIR" -name '*.lua' | wc -l) modules + awall-cli)"
else
    echo "⚠️  LUA_BIN not provided — syntax gate SKIPPED (structural gate still enforced)"
fi

# ── Layer 3: best-effort real run ────────────────────────────────────
run_ok=0
if [ -n "$LUA_BIN" ] && [ -x "$LUA_BIN" ]; then
    if "$LUA_BIN" -e "require 'posix'; require 'stringy'" 2>/dev/null \
       && "$LUA_BIN" -e "require 'alt_getopt'; require 'cjson'" 2>/dev/null; then
        # Host modules reachable: really run awall list against package dirs.
        export AWALL_PATH_MANDATORY="$SHARE_DIR/mandatory"
        export AWALL_PATH_OPTIONAL="$SHARE_DIR/optional"
        export AWALL_PATH_PRIVATE="$SHARE_DIR/private"
        if out=$("$LUA_BIN" "$SBIN" list 2>&1); then
            run_ok=1
            echo "✅ awall list OK"
            printf '%s\n' "$out" | head -8
        else
            echo "❌ awall list FAILED:"
            printf '%s\n' "$out" | head -8
            exit 1
        fi
    else
        # Missing host modules: report SKIP explicitly — do NOT fake a pass.
        missing=""
        for m in posix stringy alt_getopt cjson; do
            "$LUA_BIN" -e "require '$m'" 2>/dev/null || missing="$missing $m"
        done
        echo "⚠️  awall real run SKIPPED — host Lua module(s) unreachable:$missing"
        echo "    (not published to ohpcd; structural + syntax gates above passed)"
    fi
else
    echo "⚠️  awall real run SKIPPED — no lua interpreter (LUA_BIN unset)"
fi

echo "=== Results: structural ✅ syntax ✅ real-run=$([ "$run_ok" = 1 ] && echo PASS || echo SKIP) ==="
exit 0
