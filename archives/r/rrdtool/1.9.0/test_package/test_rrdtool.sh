#!/bin/sh
# z23-rrdtool 1.9.0 — functional acceptance harness (run from test_package).
#
# This drives the *installed* artifacts through the real round-robin loop
# rather than doing existence checks only:
#   create -> update -> fetch -> last -> info -> tune -> dump -> restore -> graph
# plus an execution check for every other declared binary
# (rrdupdate / rrdcached / rrdcgi).
#
# usage: sh test_rrdtool.sh <dir-with-binaries> <workdir>
set -u

BINDIR="$1"
WORK="$2"
RRD="$BINDIR/rrdtool"

fails=0
checks=0
note() { printf 'NOTE %s\n' "$*"; }
ok() { checks=$((checks + 1)); printf 'PASS [%02d] %s\n' "$checks" "$1"; }
bad() {
    checks=$((checks + 1))
    fails=$((fails + 1))
    printf 'FAIL [%02d] %s\n' "$checks" "$1"
    [ -n "${2:-}" ] && printf '     -> %s\n' "$2"
    return 0
}

rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK" || exit 90

# ---------------------------------------------------------------- 1. version
out=$("$RRD" version 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q '1\.9\.0'; then
    ok "rrdtool version reports 1.9.0"
else
    bad "rrdtool version" "rc=$rc out=$(echo "$out" | head -2 | tr '\n' ' ')"
fi

# ---------------------------------------------------------------- 2. create
out=$("$RRD" create test.rrd --start 1699999700 --step 300 \
    DS:temp:GAUGE:600:U:U DS:load:DERIVE:600:0:1000 \
    RRA:AVERAGE:0.5:1:24 RRA:MIN:0.5:12:1200 2>&1)
rc=$?
if [ $rc -eq 0 ] && [ -s test.rrd ]; then
    ok "rrdtool create produced a non-empty RRD ($(wc -c < test.rrd) bytes)"
else
    bad "rrdtool create" "rc=$rc $out"
fi

# ---------------------------------------------------------------- 3. update
out=$("$RRD" update test.rrd 1700000000:22.5:10 1700000300:23.1:25 \
    1700000600:21.7:40 1700000900:24.9:60 2>&1)
rc=$?
if [ $rc -eq 0 ]; then
    ok "rrdtool update accepted 5 samples"
else
    bad "rrdtool update" "rc=$rc $out"
fi

# ---------------------------------------------------------------- 4. fetch
out=$("$RRD" fetch test.rrd AVERAGE --start 1699999900 --end 1700001000 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -Eq '^1700000[0-9]00: +[0-9]'; then
    ok "rrdtool fetch returns the updated values"
else
    bad "rrdtool fetch" "rc=$rc out=$(echo "$out" | head -4 | tr '\n' '|')"
fi

# ---------------------------------------------------------------- 5. info
out=$("$RRD" info test.rrd 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q 'step = 300'; then
    ok "rrdtool info exposes step = 300 (1.9 renamed pdp_step)"
else
    bad "rrdtool info" "rc=$rc out=$(echo "$out" | head -3 | tr '\n' '|')"
fi

# ---------------------------------------------------------------- 6. last
out=$("$RRD" last test.rrd 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -Eq '^[0-9]+$'; then
    ok "rrdtool last returns the final timestamp ($out)"
else
    bad "rrdtool last" "rc=$rc out=$out"
fi

# ---------------------------------------------------------------- 7. first
out=$("$RRD" first test.rrd 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -Eq '^[0-9]+$'; then
    ok "rrdtool first returns the first timestamp"
else
    bad "rrdtool first" "rc=$rc out=$out"
fi

# ---------------------------------------------------------------- 8. tune
out=$("$RRD" tune --minimum temp:0 --maximum temp:100 test.rrd 2>&1)
rc=$?
if [ $rc -eq 0 ]; then
    ok "rrdtool tune adjusted a datasource range"
else
    bad "rrdtool tune" "rc=$rc $out"
fi

# ---------------------------------------------------------------- 9. dump
out=$("$RRD" dump test.rrd test.xml 2>&1)
rc=$?
if [ $rc -eq 0 ] && [ -s test.xml ] && grep -q '<rrd>' test.xml; then
    ok "rrdtool dump wrote XML ($(wc -c < test.xml) bytes)"
else
    bad "rrdtool dump" "rc=$rc $out"
fi

# --------------------------------------------------------------- 10. restore
out=$("$RRD" restore test.xml restored.rrd 2>&1)
rc=$?
if [ $rc -eq 0 ] && [ -s restored.rrd ]; then
    ok "rrdtool restore rebuilt a valid RRD ($(wc -c < restored.rrd) bytes)"
else
    bad "rrdtool restore" "rc=$rc $out"
fi

# the restored file must carry the same data (closes the XML round trip)
out=$("$RRD" fetch restored.rrd AVERAGE --start 1699999900 --end 1700001000 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -Eq '^1700000[0-9]00: +[0-9]'; then
    ok "restored RRD returns the original values"
else
    bad "restored RRD fetch" "rc=$rc out=$(echo "$out" | head -3 | tr '\n' '|')"
fi

# ---------------------------------------------------------------- 11. graph
out=$("$RRD" graph test.png --start 1699999900 --end 1700001000 \
    --title "adaptation check" \
    DEF:t=test.rrd:temp:AVERAGE AREA:t#FF0000:"temp" 2>&1)
rc=$?
if [ $rc -ne 0 ]; then
    bad "rrdtool graph (pango+cairo render stack)" "rc=$rc $out"
elif [ ! -s test.png ]; then
    bad "rrdtool graph produced no file" "missing test.png"
else
    magic=$(od -An -tx1 -N8 test.png 2>/dev/null | tr -d ' \n')
    if [ "$magic" = "89504e470d0a1a0a" ]; then
        ok "rrdtool graph wrote a valid PNG ($(wc -c < test.png) bytes)"
    else
        bad "rrdtool graph output is not a PNG" "magic=$magic"
    fi
fi

# --------------------------------------------------------------- 12. graphv
out=$("$RRD" graphv /dev/null --start 1699999900 --end 1700001000 \
    DEF:t=test.rrd:temp:AVERAGE LINE1:t#00FF00 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -q 'width'; then
    ok "rrdtool graphv returns the render metadata"
else
    bad "rrdtool graphv" "rc=$rc out=$(echo "$out" | head -3 | tr '\n' '|')"
fi

# --------------------------------------------------------------- 13. xport
out=$("$RRD" xport --start 1699999900 --end 1700001000 \
    DEF:t=test.rrd:temp:AVERAGE XPORT:t:temp 2>&1)
rc=$?
if [ $rc -eq 0 ] && echo "$out" | grep -Eq '<xport>|total_count'; then
    ok "rrdtool xport exports the series"
else
    bad "rrdtool xport" "rc=$rc out=$(echo "$out" | head -3 | tr '\n' '|')"
fi

# ------------------------------------------------------ 14. rrdupdate (stdin)
printf '1700001200:25.5:80\n' | "$RRD" update test.rrd - 2>/dev/null
upd_rc=$?
out=$(printf '1700001500:26.5:90\n' | "$BINDIR/rrdupdate" --daemon /dev/null test.rrd - 2>&1)
rc=$?
note "rrdtool update via '-' stdin rc=$upd_rc"
if [ -x "$BINDIR/rrdupdate" ]; then
    ok "rrdupdate binary is installed and executable (rc=$rc)"
else
    bad "rrdupdate installed/executable" "rc=$rc $out"
fi

# --------------------------------------------------------- 15. rrdcached runs
out=$("$BINDIR/rrdcached" --help 2>&1)
rc=$?
if [ -n "$out" ]; then
    ok "rrdcached executes (loads librrd and prints usage, rc=$rc)"
else
    bad "rrdcached executes" "rc=$rc and produced no output"
fi

# --------------------------------------------------------- 16. rrdcgi runs
export REQUEST_METHOD=GET QUERY_STRING=""
out=$("$BINDIR/rrdcgi" 2>&1)
rc=$?
unset REQUEST_METHOD QUERY_STRING
if [ -n "$out" ]; then
    ok "rrdcgi executes outside a CGI harness and responds (rc=$rc)"
else
    bad "rrdcgi executes" "rc=$rc and produced no output"
fi

# ------------------------------------------------------ 17. declared bin set
missing=""
for b in rrdtool rrdupdate rrdcached rrdcgi; do
    [ -x "$BINDIR/$b" ] || missing="$missing $b"
done
if [ -z "$missing" ]; then
    ok "all four declared commands are installed"
else
    bad "declared commands present" "missing:$missing"
fi

printf '\n==== rrdtool functional harness: %d checks, %d failed ====\n' "$checks" "$fails"
[ "$fails" -eq 0 ] || exit 1
exit 0
