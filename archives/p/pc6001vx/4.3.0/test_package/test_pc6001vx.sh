#!/data/service/hnp/bin/bash
# test_package/test_pc6001vx.sh — consumer smoke test for the packaged
# PC6001VX emulator (HarmonyOS PC aarch64, Qt6 build).
#
# Why these entry points: PC6001VX constructs QApplication *before* it parses
# its command line, so every run needs a QPA platform plugin — the OHOS qtbase
# package ships exactly `minimal` and `offscreen`. Upstream's -v/--version and
# -h/--help handling ends inside QCommandLineParser, i.e. before the emulator
# window, the emulation thread, the ROM bank and the audio device are touched
# (the normal startup path would block in the Qt event loop forever, which is
# useless as a CI smoke test). So the packaged binary is exercised on
#   1. the headless offscreen QPA plugin (-v / -h / bad-argument exit codes),
#   2. the minimal QPA plugin,
#   3. the missing-plugin path: without QT_QPA_PLATFORM the default xcb plugin
#      does not exist on OHOS, Qt must print its diagnostics and exit non-zero
#      instead of running the emulator without a display.
set -u

BINDIR="${1:?usage: test_pc6001vx.sh <bin-dir>}"
BIN="$BINDIR/PC6001VX"
TMPDIR_RUN="$(mktemp -d)"
trap 'rm -rf "$TMPDIR_RUN"' EXIT

PASS=0
FAIL=0
ok()   { echo "[ok] $1"; PASS=$((PASS + 1)); }
bad()  { echo "[fail] $1"; FAIL=$((FAIL + 1)); }
same() { if [ "$2" = "$3" ]; then ok "$1"; else bad "$1 (expected '$2', got '$3')"; fi; }

echo "== pc6001vx consumer smoke test =="
echo "binary : $BIN"
echo "sha256 : $(sha256sum "$BIN" | cut -d' ' -f1)"

# ---------------------------------------------------------------- 1) presence
if [ -x "$BIN" ]; then
    ok "packaged bin/PC6001VX exists and is executable"
else
    bad "packaged bin/PC6001VX is missing or not executable"
    echo "RESULT: $PASS passed, $FAIL failed"
    exit 1
fi

# --------------------------------------------- 2) version banner, headless QPA
OUT="$TMPDIR_RUN/version.out"
ERR="$TMPDIR_RUN/version.err"
QT_QPA_PLATFORM=offscreen "$BIN" --version >"$OUT" 2>"$ERR"
same "offscreen QPA: --version exits 0" "0" "$?"
same "offscreen QPA: --version prints the upstream banner" \
     "PC6001VX 4.3.0" "$(cat "$OUT")"

# ------------------------------------------------- 3) help text, headless QPA
QT_QPA_PLATFORM=offscreen "$BIN" --help >"$TMPDIR_RUN/help.out" 2>&1
same "offscreen QPA: --help exits 0" "0" "$?"
if grep -q -- "-s, --safemode" "$TMPDIR_RUN/help.out"; then
    ok "--help documents -s/--safemode"
else
    bad "--help does not document -s/--safemode"
fi
if grep -q -- "-l, --loadstate" "$TMPDIR_RUN/help.out"; then
    ok "--help documents -l/--loadstate"
else
    bad "--help does not document -l/--loadstate"
fi
if grep -q -- "-v, --version" "$TMPDIR_RUN/help.out"; then
    ok "--help documents -v/--version"
else
    bad "--help does not document -v/--version"
fi

# ---------------------------------------------- 4) minimal QPA plugin works too
QT_QPA_PLATFORM=minimal "$BIN" --version >"$TMPDIR_RUN/minimal.out" 2>&1
same "minimal QPA: --version exits 0" "0" "$?"
same "minimal QPA: --version prints the upstream banner" \
     "PC6001VX 4.3.0" "$(cat "$TMPDIR_RUN/minimal.out")"

# --------------------------- 5) graceful failure with a bad command line
QT_QPA_PLATFORM=offscreen "$BIN" --no-such-option >"$TMPDIR_RUN/bad.out" 2>&1
same "unknown option exits non-zero" "1" "$?"
if grep -q "Unknown option 'no-such-option'" "$TMPDIR_RUN/bad.out"; then
    ok "unknown option prints a diagnostic"
else
    bad "unknown option prints no diagnostic"
fi

# ---------------- 6) graceful failure when no usable display plugin is found
"$BIN" --version >"$TMPDIR_RUN/noqpa.out" 2>&1
NORC=$?
if [ "$NORC" -ne 0 ]; then
    ok "missing QPA plugin exits non-zero (rc=$NORC)"
else
    bad "missing QPA plugin exited 0 — display dependency not detected"
fi
if grep -q "Could not find the Qt platform plugin" "$TMPDIR_RUN/noqpa.out"; then
    ok "missing QPA plugin prints the Qt diagnostic"
else
    bad "missing QPA plugin prints no Qt diagnostic"
fi
if grep -q "Available platform plugins are: minimal, offscreen" \
        "$TMPDIR_RUN/noqpa.out"; then
    ok "diagnostic lists the packaged platform plugins (minimal, offscreen)"
else
    bad "diagnostic does not list the packaged platform plugins"
fi

echo "RESULT: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ]
