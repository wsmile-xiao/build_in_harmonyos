#!/bin/sh
# test_package/test.sh — consumer smoke test for the alacritty executable
# Runs in conanrun env (PATH includes installed bin/).
# Counts each real case and emits the HMBS_TEST_PACKAGE_RESULT marker.
#
# alacritty is a GUI terminal emulator: window creation needs a Wayland
# compositor, which neither the CI worker nor the headless preflight
# provides. The consumer cases therefore cover the real, headless-safe
# CLI surface: --version, --help, subcommand help, error handling and
# the offline config-migration subcommand (alacritty migrate converts a
# YAML config to TOML with zero display dependency).
#
# HMBS 平台诊断 shell_getcwd：HNP bash 在 HMFS/HMDFS 工作目录启动时
# getcwd 失败，会在 stderr 打印一条无害的 `shell-init:` 警告（由注入的
# /bin/sh 执行本脚本，不受影响；比对输出前剥离该环境产物行）。
set -uo pipefail

PASS=0
FAIL=0

ALACRITTY=alacritty

# alacritty links libc++_shared.so / _Unwind_* from the OHOS system runtime
# in /system/lib64. The conanrun env (and the device default shell env,
# whose /system/lib64 entry is whitespace-corrupted) may not carry it on
# LD_LIBRARY_PATH, so prepend the system lib dir explicitly. Verified on
# device: with /system/lib64 present the packaged binary runs clean; with
# the malformed default it fails with "Error loading shared library
# libc++_shared.so" + _Unwind_* reloc errors.
case ":${LD_LIBRARY_PATH:-}:" in
    *:/system/lib64:*) ;;
    *) LD_LIBRARY_PATH="/system/lib64${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" ;;
esac
export LD_LIBRARY_PATH

# cd to a writable directory (HMBS TMPDIR; OHOS /tmp is read-only)
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" || true

# strip harmless HNP bash getcwd diagnostics from captured output
clean() { sed '/^shell-init:/d'; }

echo "[test] alacritty --version"
VERSION_OUT=$("$ALACRITTY" --version 2>&1 | clean)
if printf '%s' "$VERSION_OUT" | grep -q "alacritty 0.17.0"; then
    PASS=$((PASS + 1))
    echo "[ok] --version prints 'alacritty 0.17.0'"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --version output unexpected: $VERSION_OUT"
fi

echo "[test] alacritty --help"
HELP_OUT=$("$ALACRITTY" --help 2>&1 | clean)
if printf '%s' "$HELP_OUT" | grep -q "Usage: alacritty" \
    && printf '%s' "$HELP_OUT" | grep -q "OpenGL terminal emulator"; then
    PASS=$((PASS + 1))
    echo "[ok] --help shows usage and description"
else
    FAIL=$((FAIL + 1))
    echo "[fail] --help output unexpected: $HELP_OUT"
fi

echo "[test] alacritty msg --help (subcommand routing)"
MSG_OUT=$("$ALACRITTY" msg --help 2>&1 | clean)
if printf '%s' "$MSG_OUT" | grep -q "Send a message to the Alacritty socket"; then
    PASS=$((PASS + 1))
    echo "[ok] msg subcommand help works"
else
    FAIL=$((FAIL + 1))
    echo "[fail] msg subcommand help unexpected: $MSG_OUT"
fi

echo "[test] invalid flag exits 2 with usage"
BOGUS_OUT=$("$ALACRITTY" --definitely-not-a-flag 2>&1 | clean)
BOGUS_RC=$?
if [ "$BOGUS_RC" -eq 2 ] && printf '%s' "$BOGUS_OUT" | grep -q "unexpected argument"; then
    PASS=$((PASS + 1))
    echo "[ok] invalid flag rejected with clap usage error (rc=2)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] invalid flag rc=$BOGUS_RC output: $BOGUS_OUT"
fi

echo "[test] alacritty migrate converts YAML config to TOML (offline)"
MIG_DIR="$(pwd)/alacritty-mig-test.$$"
mkdir -p "$MIG_DIR"
printf 'font:\n  size: 12.0\n  normal:\n    family: monospace\nwindow:\n  opacity: 0.9\n' \
    > "$MIG_DIR/old.yml"
MIG_OUT=$("$ALACRITTY" migrate -c "$MIG_DIR/old.yml" -d 2>&1 | clean)
MIG_RC=$?
if [ "$MIG_RC" -eq 0 ] \
    && printf '%s' "$MIG_OUT" | grep -q '^\[font\]' \
    && printf '%s' "$MIG_OUT" | grep -q 'size = 12.0'; then
    PASS=$((PASS + 1))
    echo "[ok] migrate converts YAML to valid TOML (rc=0, [font] section present)"
else
    FAIL=$((FAIL + 1))
    echo "[fail] migrate rc=$MIG_RC output: $MIG_OUT"
fi
rm -rf "$MIG_DIR" 2>/dev/null || true

echo "[test] ELF architecture check"
ALACRITTY_BIN=$(command -v "$ALACRITTY" 2>/dev/null || printf '%s' "$ALACRITTY")
if command -v file >/dev/null 2>&1; then
    FILE_OUT=$(file "$ALACRITTY_BIN" 2>&1)
else
    FILE_OUT=$(readelf -h "$ALACRITTY_BIN" 2>&1)
fi
if printf '%s' "$FILE_OUT" | grep -qE "arm64|AArch64|Machine:.*AArch64"; then
    PASS=$((PASS + 1))
    echo "[ok] binary is arm64 ELF"
else
    FAIL=$((FAIL + 1))
    echo "[fail] architecture check unexpected: $FILE_OUT"
fi

echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":$([ "$FAIL" -eq 0 ] && echo true || echo false),\"command\":\"/bin/sh test.sh\",\"discovered\":6,\"passedCount\":$PASS}"

if [ "$FAIL" -ne 0 ]; then
    echo "[fail] $FAIL case(s) failed, $PASS passed"
    exit 1
fi
echo "[ok] all $PASS test_package cases passed"
