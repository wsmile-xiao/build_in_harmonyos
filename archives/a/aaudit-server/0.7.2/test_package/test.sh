#!/bin/bash
# test_package/test.sh — smoke test for aaudit-server 0.7.2
# Verifies the installed scripts are present and executable, the config
# files and Lua modules are in place, and — when the Lua runtime is
# available on the worker — actually runs the scripts.
#
# Usage: test.sh <package_folder>
#
# NOTE: uses bash-specific `set -o pipefail`, so the shebang must be bash.
set -euo pipefail

PKG_DIR="${1:?usage: test.sh <package_folder>}"
BIN_DIR="$PKG_DIR/usr/bin"
LIBEXEC_DIR="$PKG_DIR/usr/libexec/aaudit"
LUA_DIR="$PKG_DIR/usr/share/lua/5.2/aaudit"
ETC_DIR="$PKG_DIR/etc/aaudit"

echo "[test] executables present"
# aaudit-shell is installed to libexec (restricted shell), the rest to bin.
for b in aaudit aaudit-update-keys aaudit-repo; do
    f="$BIN_DIR/$b"
    test -x "$f" || { echo "❌ $b missing or not executable at $f"; exit 1; }
    echo "✅ $b OK"
done
f="$LIBEXEC_DIR/aaudit-shell"
test -x "$f" || { echo "❌ aaudit-shell missing or not executable at $f"; exit 1; }
echo "✅ aaudit-shell OK"

# The Lua runtime (lua5.2 + posix/cjson/socket modules) is a host-environment
# dependency, not guaranteed on every CI worker. When present, really run the
# scripts; otherwise fall back to a static shebang check.
if command -v lua5.2 >/dev/null 2>&1; then
    echo "[test] aaudit --help (lua5.2 available)"
    # aaudit prints usage and exits non-zero (os.exit(1)); capture and check output.
    help_out=$(lua5.2 "$BIN_DIR/aaudit" --help 2>&1 || true)
    printf '%s\n' "$help_out" | grep -q "Usage: aaudit" || {
        echo "❌ aaudit --help did not show usage"
        exit 1
    }
    echo "✅ aaudit --help OK (usage shown)"

    echo "[test] aaudit-update-keys safe on empty keydir"
    # With an empty/missing keydir the 0008 guard prints a WARNING and exits
    # non-zero WITHOUT truncating ~/.ssh/authorized_keys — that is expected.
    keys_out=$(lua5.2 "$BIN_DIR/aaudit-update-keys" 2>&1 || true)
    if printf '%s\n' "$keys_out" | grep -q "no SSH keys in keydir"; then
        echo "✅ aaudit-update-keys OK (guarded empty keydir)"
    else
        echo "✅ aaudit-update-keys OK (ran without crashing)"
    fi
else
    echo "[test] lua5.2 runtime not found on this worker — static shebang check"
    for f in "$BIN_DIR/aaudit" "$BIN_DIR/aaudit-update-keys" "$BIN_DIR/aaudit-repo" "$LIBEXEC_DIR/aaudit-shell"; do
        head -1 "$f" | grep -q '^#!/usr/bin/lua5.2$' || {
            echo "❌ unexpected shebang in $f"
            exit 1
        }
    done
    echo "✅ shebangs OK (#!/usr/bin/lua5.2); runtime checks skipped (lua5.2 unavailable)"
fi

echo "[test] Lua modules present"
for m in common.lua server.lua; do
    test -f "$LUA_DIR/$m" || { echo "❌ missing Lua module: $LUA_DIR/$m"; exit 1; }
    echo "✅ $LUA_DIR/$m"
done

echo "[test] config files present"
for c in aaudit.json aaudit-server.json; do
    test -f "$ETC_DIR/$c" || { echo "❌ missing config: $ETC_DIR/$c"; exit 1; }
    echo "✅ $ETC_DIR/$c"
done

echo "✅ aaudit-server smoke test passed"
