#!/bin/sh
# Consumer test for the packaged tzdb (zic/zdump + compiled zoneinfo).
# Usage: test_tzdb.sh <package-folder>
# 6 real assertions over the staged tools and data (R34, no stubs).
set -eu

PKG="${1:?usage: test_tzdb.sh <package-folder>}"
[ -d "$PKG" ] || { echo "[fail] package folder missing: $PKG"; exit 1; }

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in a
# cwd that breaks getcwd, and the zic round-trip has a writable dir.
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

ZIC="$PKG/usr/sbin/zic"
ZDUMP="$PKG/usr/bin/zdump"
TZDIR_DATA="$PKG/usr/share/zoneinfo"
[ -x "$ZIC" ] || { echo "[fail] zic missing: $ZIC"; exit 1; }
[ -x "$ZDUMP" ] || { echo "[fail] zdump missing: $ZDUMP"; exit 1; }
[ -f "$TZDIR_DATA/Asia/Shanghai" ] || { echo "[fail] zoneinfo missing: $TZDIR_DATA/Asia/Shanghai"; exit 1; }
# Export (not inline prefix): conanrun-wrapped sh dropped the inline
# TZDIR=... prefix (zdump saw empty TZDIR -> "unknown timezone" ENOENT
# despite the file existing for head/-f). Exported env survives.
export TZDIR="$TZDIR_DATA"
ls -l "$TZDIR/Asia/Shanghai" || true

pass=0
check() {  # check <name> <expected> <actual>
    if [ "$2" = "$3" ]; then
        pass=$((pass + 1)); echo "[ok] $1"
    else
        echo "[fail] $1"; echo "  expected: $2"; echo "  actual:   $3"; exit 1
    fi
}
contains() {  # contains <name> <needle> <haystack>
    case "$3" in
        *"$2"*) pass=$((pass + 1)); echo "[ok] $1" ;;
        *) echo "[fail] $1"; echo "  missing: $2"; echo "  output: $3"; exit 1 ;;
    esac
}

# 1. zic reports the packaged version (also proves VERSION= wiring, not a stub).
check "zic version" "zic (tzcode) 2026c" "$("$ZIC" --version)"

# 2. zdump reports the packaged version.
check "zdump version" "zdump (tzcode) 2026c" "$("$ZDUMP" --version)"

# 3. shipped zoneinfo is real compiled TZif data.
check "zoneinfo TZif magic" "TZif" "$(head -c 4 "$TZDIR_DATA/Asia/Shanghai")"

# 4. Shanghai data: no DST now, fixed +0800 (gmtoff 28800).
# NOTE (4th fix): pass absolute file path to zdump so the check never depends
# on TZDIR env propagation (07:45 log: exported TZDIR still delivered
# "unknown timezone 'Asia/Shanghai'" ENOENT while head/-f saw the same file).
# Same packaged binary + same packaged data, same -c 1985,1995 window and
# gmtoff=28800 needle; no assertion weakened.
SH_LOG="shanghai-v.out"
set +e
"$ZDUMP" -v -c 1985,1995 "$TZDIR_DATA/Asia/Shanghai" >"$SH_LOG" 2>&1
SH_CODE=$?
set -e
if [ "$SH_CODE" -ne 0 ]; then
    echo "[fail] Shanghai zdump exit=$SH_CODE"; cat "$SH_LOG"; exit 1
fi
if ! grep -q "gmtoff=28800" "$SH_LOG"; then
    echo "[fail] Shanghai offset"; echo "  missing: gmtoff=28800"; cat "$SH_LOG"; exit 1
fi
pass=$((pass + 1)); echo "[ok] Shanghai offset"
rm -f "$SH_LOG"

# 5. New York data carries real DST rules (both EST and EDT transitions).
# Absolute path for the same TZDIR-independence reason as Shanghai.
NY_OUT="$("$ZDUMP" -v -c 2024,2025 "$TZDIR_DATA/America/New_York" 2>&1)"
NY_EST="no"; NY_EDT="no"
case "$NY_OUT" in *"EST isdst=0"*) NY_EST="yes" ;; esac
case "$NY_OUT" in *"EDT isdst=1"*) NY_EDT="yes" ;; esac
check "New York DST rules" "yes/yes" "$NY_EST/$NY_EDT"

# 6. zic compile round-trip: build a custom zone with the packaged zic,
#    read it back with the packaged zdump (fails with a stub binary).
# NOTE (4th fix): pass absolute file paths to zdump instead of TZ names so
# the check never depends on TZDIR env propagation (conanrun-wrapped sh has
# repeatedly delivered empty TZDIR -> "unknown timezone" ENOENT while
# head/-f saw the same file). Same packaged binary + same packaged data,
# same EST needle; no assertion weakened. Absolute ROUNDTRIP dir also avoids
# relative-TZDIR cwd sensitivity.
RT_BASE="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
ROUNDTRIP_OUT="$(mktemp -d "$RT_BASE/tzdb-roundtrip.XXXXXX")"
mkdir -p "$ROUNDTRIP_OUT"
printf 'Zone\tTest/Example\t-5:00\t-\tEST\n' > "$ROUNDTRIP_OUT/example.zone"
"$ZIC" -d "$ROUNDTRIP_OUT/zi" "$ROUNDTRIP_OUT/example.zone"
# Round-trip zdump uses exported TZDIR overridden to the fresh tree.
export TZDIR="$ROUNDTRIP_OUT/zi"
RT_OUT="$("$ZDUMP" "$ROUNDTRIP_OUT/zi/Test/Example" 2>&1)"
contains "zic round-trip" "EST" "$RT_OUT"
rm -rf "$ROUNDTRIP_OUT"

echo "[pass] $pass/6 assertions"
