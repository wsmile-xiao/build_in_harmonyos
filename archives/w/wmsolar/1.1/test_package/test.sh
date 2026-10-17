#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for wmsolar
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binaries.
set -euo pipefail

# OHOS: libc++_shared.so lives in /system/lib64, which is not on the conanrun
# LD_LIBRARY_PATH by default; append it so the C++ runtime resolves.
export LD_LIBRARY_PATH="/system/lib64:${LD_LIBRARY_PATH:-}"

echo "[test] wmSolar binary present in PATH"
command -v wmSolar >/dev/null
echo "OK: $(command -v wmSolar)"

echo "[test] wmSolar loads X11 dependency chain (XOpenDisplay reached)"
# OHOS has no X server, so XOpenDisplay fails with "can't open display".
# Reaching that message proves the Xpm/X11/Xext dependency chain loaded.
OUTPUT=$(wmSolar 2>&1) || true
echo "$OUTPUT" | grep -q "can't open display"
echo "OK: wmSolar reached XOpenDisplay (deps OK, no X server expected on OHOS)"

echo "[test] DarkCal end-to-end consumer use case (darkest-hours computation)"
# DarkCal is the upstream console astronomy program (no X11). It consumes a
# .cfg next to the binary and writes a per-day table (MonthYYYY.txt). We run
# a real month/year computation and verify the produced table, i.e. a genuine
# end-to-end flow through the package's calculation pipeline.
command -v DarkCal >/dev/null
WORKDIR="${TMPDIR:-/storage/Users/currentUser/tmp}/wmsolar-test-$$"
trap 'rm -rf "$WORKDIR"' EXIT
mkdir -p "$WORKDIR"
cat > "$WORKDIR/DarkCal.cfg" <<'EOF'
longitude=121.47
latitude=31.23
timeZone=8
ignoreDST=false
useUTC=false
htmlOutput=false
tabDelimited=true
EOF
(cd "$WORKDIR" && DarkCal 9 2026) >/dev/null 2>&1
test -f "$WORKDIR/September2026.txt"
grep -q "September, 2026" "$WORKDIR/September2026.txt"
grep -q "Darkest Hours" "$WORKDIR/September2026.txt"
LINES=$(grep -c $'\t' "$WORKDIR/September2026.txt" || true)
if [ "${LINES:-0}" -lt 20 ]; then
    echo "FAIL: DarkCal table has only ${LINES:-0} rows (expected >= 20)"
    exit 1
fi
echo "OK: DarkCal produced $LINES per-day table rows (end-to-end)"
# WORKDIR cleanup is handled by the EXIT trap above (kept for both success and failure paths)