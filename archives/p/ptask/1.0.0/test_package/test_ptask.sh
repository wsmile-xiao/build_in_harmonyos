#!/data/service/hnp/bin/bash
# test_package/test_ptask.sh — HarmonyOS PC package test for ptask 1.0.0.
#
# Usage: test_ptask.sh <packaged ptask binary> <package folder>
#
# ptask is a GTK+ 3 desktop application and HarmonyOS PC has no X server,
# so this test only drives the headless paths the adaptation provides:
#   * the upstream CLI contract (--version / --help)
#   * the adaptation's --selftest (programmatic checks over the production
#     pstr/ptime helpers and the complete taskwarrior import path)
#   * the no-display error path, which proves the packaged binary really
#     loads and initialises the GTK stack it links
#   * the HarmonyOS-specific packaging facts (ELF .codesign section,
#     compiled gsettings schema, desktop entry, glade UI file)

set -u

BIN="${1:?packaged ptask binary path required}"
PKG="${2:?package folder required}"

pass=0
fail=0

ok()  { printf 'ok   %s\n' "$1"; pass=$((pass + 1)); }
bad() { printf 'FAIL %s\n' "$1"; fail=$((fail + 1)); }

echo "[test] binary : $BIN"
echo "[test] package: $PKG"

# ---- 1. package presence ------------------------------------------------
if [ -x "$BIN" ]; then
    ok "bin/ptask installed and executable"
else
    bad "bin/ptask missing or not executable"
fi

if [ -f "$PKG/share/ptask/ptask.glade" ] \
   && grep '<interface>' "$PKG/share/ptask/ptask.glade" > /dev/null 2>&1; then
    ok "share/ptask/ptask.glade installed and is a GtkBuilder file"
else
    bad "share/ptask/ptask.glade missing or not a GtkBuilder file"
fi

if [ -f "$PKG/share/applications/ptask.desktop" ]; then
    ok "share/applications/ptask.desktop installed"
else
    bad "share/applications/ptask.desktop missing"
fi

if [ -f "$PKG/share/glib-2.0/schemas/gschemas.compiled" ]; then
    ok "gsettings schema compiled into the package"
else
    bad "share/glib-2.0/schemas/gschemas.compiled missing"
fi

if [ -f "$PKG/share/icons/hicolor/scalable/apps/ptask.svg" ]; then
    ok "hicolor application icon installed"
else
    bad "share/icons/hicolor/scalable/apps/ptask.svg missing"
fi

# ---- 2. upstream CLI contract -------------------------------------------
out=$("$BIN" --version 2>&1)
rc=$?
first=$(printf '%s\n' "$out" | head -n 1)
if [ "$rc" -eq 0 ] && [ "$first" = "ptask 1.0.0" ]; then
    ok "--version prints 'ptask 1.0.0' and exits 0"
else
    bad "--version rc=$rc first line='$first'"
fi

out=$("$BIN" --help 2>&1)
rc=$?
if [ "$rc" -eq 0 ] \
   && printf '%s' "$out" | grep 'force-unsupported-taskwarrior' > /dev/null 2>&1 \
   && printf '%s' "$out" | grep 'selftest' > /dev/null 2>&1; then
    ok "--help exits 0 and documents the upstream and adaptation options"
else
    bad "--help rc=$rc output does not list the expected options"
fi

out=$("$BIN" --no-such-option 2>&1)
rc=$?
if [ "$rc" -eq 1 ] \
   && printf '%s' "$out" | grep 'help' > /dev/null 2>&1; then
    ok "unknown option is rejected with exit status 1"
else
    bad "unknown option rc=$rc (expected 1)"
fi

out=$("$BIN" unexpected-argument 2>&1)
rc=$?
if [ "$rc" -ne 0 ]; then
    ok "unexpected position argument is rejected"
else
    bad "unexpected position argument was accepted"
fi

# ---- 3. the HarmonyOS specific headless self test ------------------------
# GSETTINGS_SCHEMA_DIR makes --selftest load the schema compiled into this
# package instead of relying on a system wide installation.
export GSETTINGS_SCHEMA_DIR="$PKG/share/glib-2.0/schemas"
selftest_out=$("$BIN" --selftest 2>&1)
rc=$?
selftest_ok=$(printf '%s\n' "$selftest_out" | grep -c '^ok  ')
selftest_fail=$(printf '%s\n' "$selftest_out" | grep -c '^FAIL')

if [ "$rc" -eq 0 ] && [ "$selftest_fail" -eq 0 ] && [ "$selftest_ok" -ge 18 ] \
   && printf '%s' "$selftest_out" | grep 'selftest: .* checks passed' > /dev/null 2>&1; then
    ok "ptask --selftest: $selftest_ok checks passed (no failures)"
else
    bad "ptask --selftest rc=$rc ok=$selftest_ok fail=$selftest_fail"
    printf '%s\n' "$selftest_out" | sed 's/^/     | /'
fi

if printf '%s\n' "$selftest_out" | grep "GSettings schema 'ptask' found" > /dev/null 2>&1; then
    ok "packaged gsettings schema is usable by the binary"
else
    bad "packaged gsettings schema was not found by the binary"
fi

# ---- 4. no-display error path (proves GTK is initialised) ----------------
no_display_out=$(DISPLAY=:99 GDK_BACKEND=x11 "$BIN" -f 2>&1)
rc=$?
if [ "$rc" -ne 0 ] \
   && printf '%s' "$no_display_out" | grep -i 'display' > /dev/null 2>&1; then
    ok "GUI launch without a display fails closed with a GTK display error"
else
    bad "no-display launch rc=$rc out='$no_display_out'"
fi

# ---- 5. HarmonyOS packaging facts ---------------------------------------
readelf_tool=""
for candidate in llvm-readelf readelf; do
    if command -v "$candidate" > /dev/null 2>&1; then
        readelf_tool="$candidate"
        break
    fi
done

if [ -n "$readelf_tool" ]; then
    sections=$("$readelf_tool" -SW "$BIN" 2>/dev/null)
    codesign_count=$(printf '%s' "$sections" | grep -c '\.codesign')
    if [ "$codesign_count" -eq 1 ]; then
        ok "packaged executable carries exactly one .codesign section"
    else
        bad "packaged executable has $codesign_count .codesign sections (expected 1)"
    fi

    needed=$("$readelf_tool" -d "$BIN" 2>/dev/null | grep NEEDED)
    if printf '%s' "$needed" | grep 'libgtk-3' > /dev/null 2>&1; then
        ok "executable links against libgtk-3"
    else
        bad "executable does not link against libgtk-3"
    fi
else
    echo "info no readelf available, skipping the ELF section checks"
fi

# ---- summary -------------------------------------------------------------
echo "[test] $pass passed, $fail failed"
if [ "$fail" -ne 0 ]; then
    exit 1
fi
exit 0
