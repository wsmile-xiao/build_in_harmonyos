#!/bin/sh
# Consumer test for the packaged tzdiff (wrapper + patched script + bundled zoneinfo).
# Usage: test_tzdiff.sh <path-to-bin/tzdiff>
set -eu

BIN="${1:?usage: test_tzdiff.sh <bin/tzdiff>}"
[ -f "$BIN" ] || { echo "[fail] $BIN missing"; exit 1; }
PREFIX=$(CDPATH= cd -- "$(dirname -- "$BIN")/.." && pwd)
TAB=$(printf '\t')
pass=0

check() {  # check <name> <expected> <actual>
    if [ "$2" = "$3" ]; then
        pass=$((pass + 1)); echo "[ok] $1"
    else
        echo "[fail] $1"; echo "  expected: $2"; echo "  actual:   $3"; exit 1
    fi
}

# platform facts (informational): which date implementation, system zoneinfo presence
if date --version 2>/dev/null | grep -q toybox; then date_impl=toybox; else date_impl=other; fi
if [ -f /usr/share/zoneinfo/UTC ]; then sys_zi=present; else sys_zi=absent; fi
echo "[info] uname=$(uname -sm) date=$date_impl /usr/share/zoneinfo=$sys_zi"

# 1. version
check "version" "tzdiff 1.2.1" "$(sh "$BIN" -v)"

# 2. bundled IANA data is real TZif
check "bundled zoneinfo TZif" "TZif" "$(head -c 4 "$PREFIX/share/zoneinfo/Asia/Tokyo")"

# 3. multi-zone table from an ISO 'T' start time (exercises -t mapping + date -d @N + absolute TZ)
#    plus an absolute-path zone argument, which must be used as-is
exp="2024-07-01 18:00 JST${TAB}2024-07-01 05:00 EDT
2024-07-01 19:00 JST${TAB}2024-07-01 06:00 EDT
2024-07-01 20:00 JST${TAB}2024-07-01 07:00 EDT"
check "multi-zone table" "$exp" "$(env -u TZDIR sh "$BIN" -HH -N -n 3 -t 2024-07-01T09:00Z "$PREFIX/share/zoneinfo/Asia/Tokyo" America/New_York)"

# 4. DST transition uses real zone rules, not a fixed offset
exp="2024-03-10 01:00 EST
2024-03-10 03:00 EDT"
check "DST transition" "$exp" "$(env -u TZDIR sh "$BIN" -HH -N -n 2 -t 2024-03-10T06:00Z America/New_York)"

# 5. short city name resolved inside the zoneinfo tree + header row
exp="Tokyo
2024-01-01 09:00 JST"
check "city lookup + header" "$exp" "$(env -u TZDIR sh "$BIN" -N -n 1 -t 2024-01-01T00:00Z Tokyo)"

# 6. [OHOS] TZDIR contract: unset -> bundled data (no /usr/share/zoneinfo on OHOS PC);
#    explicit TZDIR is honoured (a bogus one must fail instead of silently falling back)
if TZDIR=/nonexistent/zoneinfo sh "$BIN" -HH -N -n 1 UTC >/dev/null 2>&1; then
    echo "[fail] bogus TZDIR was not honoured"; exit 1
fi
check "TZDIR override honoured" "2024-07-01 09:00 UTC" \
    "$(TZDIR="$PREFIX/share/zoneinfo" sh "$BIN" -HH -N -n 1 -t 2024-07-01T09:00Z UTC)"

# 7. localtime column matches the system date(1) for the same instant
local_exp=$(date -d @1719824400 +'%F %R %Z')
check "localtime column" "2024-07-01 09:00 UTC${TAB}${local_exp}" \
    "$(env -u TZDIR sh "$BIN" -HH -n 1 -t 2024-07-01T09:00Z UTC)"

# 8. PATH lookup through the wrapper's shebang
check "PATH lookup" "tzdiff 1.2.1" "$(tzdiff -v)"

echo "[pass] $pass/8 assertions (date=$date_impl, system zoneinfo=$sys_zi)"
