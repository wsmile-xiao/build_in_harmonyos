#!/bin/sh
# POSIX shell only (no `set -o pipefail`: it is not in POSIX and the CI worker's
# /bin/sh is not guaranteed to be a shell that has it).
# `set -e` is deliberately NOT used either: this harness has to keep running
# after a failing assertion so it can report the full count, and the pre-fix run
# is exactly the case that proves it matters -- the analysis crashed at assertion
# 5, and the surviving 6 assertions are what produced `pass=4 fail=6`
# (create-06.log:576).  With `set -e` the script would have died at that SIGSEGV
# and the counter line would never have been printed.  Every external command's
# status is captured explicitly rather than left to abort the script.
# `set -u` alone catches the failure mode that matters here: a typo'd var.
set -u
# Consumer test for isoqlog 2.2.1 (HarmonyOS PC).
#
# isoqlog is an application package and upstream ships no automated test
# suite (no "check" target in any Makefile.am / Makefile.in), so behaviour is
# verified here as a real user of the program: a sendmail-format log dated
# *today* is analysed and the generated HTML reports are asserted to contain
# the parsed addresses and byte counts.  The log must be generated at run time
# because Parser.c:check_syslog_date() only accepts lines whose month/day
# match the machine's local date, so a static fixture would rot across days
# and fail on CI on the first of every month.
#
# Usage: sh test.sh <path-to-isoqlog-binary> <package-folder>
BIN="${1:-}"
PKG="${2:-}"

if [ ! -x "$BIN" ]; then
    echo "ISOQLOG_TEST_FAIL binary not executable: $BIN"
    exit 1
fi
if [ ! -f "$PKG/share/isoqlog/htmltemp/daily.html" ]; then
    echo "ISOQLOG_TEST_FAIL packaged html template missing under $PKG/share/isoqlog/htmltemp"
    exit 1
fi
if [ ! -f "$PKG/share/isoqlog/lang/english" ]; then
    echo "ISOQLOG_TEST_FAIL packaged lang/english missing"
    exit 1
fi

# Anchor the scratch dir to the cwd that conan creates for test(), never to
# TMPDIR: on the device TMPDIR points at $HOME and HMDFS would then receive
# stray files in the home root.
WORK="$PWD/isoqlog-tp.$$"
rm -rf "$WORK"
mkdir -p "$WORK/out" || { echo "ISOQLOG_TEST_FAIL cannot create $WORK"; exit 1; }
trap 'rm -rf "$WORK"' EXIT INT TERM

pass=0
failn=0
ok() { pass=$((pass + 1)); printf '  [ok] %s\n' "$1"; }
no() { failn=$((failn + 1)); printf '  [FAIL] %s\n' "$1"; }

# ---------------------------------------------------------------- 1: -h usage
out=$("$BIN" -h 2>&1)
rc=$?
if [ "$rc" = 0 ] && echo "$out" | grep -q 'Usage: isoqlog'; then
    ok "-h exits 0 and prints the usage line"
else
    no "-h rc=$rc out=$out"
fi

# -------------------------------------------------------------- 2: -v version
out=$("$BIN" -v 2>&1)
rc=$?
if [ "$rc" = 0 ] && echo "$out" | grep -q 'EnderUNIX Isoqlog 2\.2\.1'; then
    ok "-v exits 0 and prints a version banner ($out)"
else
    no "-v rc=$rc out=$out"
fi

# ----------------------------------------------- 3: unreadable config rejected
"$BIN" -f "$WORK/does-not-exist.conf" >/dev/null 2>&1
rc=$?
if [ "$rc" != 0 ]; then
    ok "missing configuration file is rejected (rc=$rc)"
else
    no "missing configuration file was accepted"
fi

# --------------------------------------------------- 4: invalid logtype exits
mkconf() {
    cat > "$1" <<EOCONF
logtype     = "$2"
logstore    = "$WORK/mail.log"
domainsfile = "$WORK/domains"
outputdir   = "$WORK/out"
htmldir     = "$PKG/share/isoqlog/htmltemp"
langfile    = "$PKG/share/isoqlog/lang/english"
hostname    = "mailhost.example.com"
maxsender   = 100
maxreceiver = 100
maxtotal    = 100
maxbyte     = 100
EOCONF
}
mkconf "$WORK/bad.conf" "nosuchlogtype"
"$BIN" -f "$WORK/bad.conf" > "$WORK/bad.out" 2>&1
rc=$?
if [ "$rc" != 0 ] && grep -q 'Invalid logtype' "$WORK/bad.out"; then
    ok "invalid logtype is rejected with the documented message (rc=$rc)"
else
    no "invalid logtype rc=$rc out=$(head -3 "$WORK/bad.out")"
fi

# ------------------------------------------- 5: real sendmail log analysis run
# syslog timestamps: "Sep 24 10:00:01" - month abbreviation and day-of-month
# without a leading zero, i.e. what date '+%b %e' produces.
STAMP=$(date '+%b %e')
printf '%s  9:59:59 mailhost sendmail[1001]: aaa0000001: from=<carol@example.com>, size=512, class=0, nrcpts=1, proto=ESMTP, daemon=MTA, relay=localhost\n' \
    "$STAMP" > "$WORK/mail.log"
cat >> "$WORK/mail.log" <<EOLF
$STAMP 10:00:01 mailhost sendmail[1234]: f8O0Y1vA001234: from=<alice@example.com>, size=1024, class=0, nrcpts=1, proto=ESMTP, daemon=MTA, relay=localhost
$STAMP 10:00:02 mailhost sendmail[1235]: f8O0Y1vA001235: to=<bob@other.org>, size=2048, class=0, nrcpts=1, proto=ESMTP, daemon=MTA, relay=localhost
$STAMP 10:00:03 mailhost sendmail[1236]: f8O0Y1vA001236: to=<dave@other.org>, size=4096, class=0, nrcpts=1, proto=ESMTP, daemon=MTA, relay=localhost
EOLF
cat > "$WORK/domains" <<EOD
example.com
other.org
EOD
mkconf "$WORK/isoqlog.conf" "sendmail"

"$BIN" -f "$WORK/isoqlog.conf" > "$WORK/run.out" 2>&1
rc=$?
if [ "$rc" = 0 ]; then
    ok "isoqlog analysed the sendmail log and exited 0"
else
    no "analysis run failed rc=$rc out=$(head -5 "$WORK/run.out")"
fi

# ------------------------------------------------ 6: index report was written
if [ -s "$WORK/out/index.html" ]; then
    ok "top-level index.html was generated and is not empty"
else
    no "index.html missing or empty ($(ls -la "$WORK/out" 2>&1 | head -5))"
fi

# ------------------------------------------- 7: per-domain reports were written
nrep=$(find "$WORK/out" -name '*.html' -type f | wc -l | tr -d ' ')
if [ "$nrep" -ge 3 ]; then
    ok "per-domain/general HTML reports were generated ($nrep files)"
else
    no "only $nrep HTML reports were generated"
fi

# ------------------------------- 8: sender address really parsed into a report
if grep -rq 'alice@example.com' "$WORK/out"; then
    ok "sender alice@example.com appears in the generated reports (from= line parsed)"
else
    no "sender address not found in reports"
fi

# ------------------------------------- 9: receiver domain parsed from to= lines
if grep -rq 'other.org' "$WORK/out"; then
    ok "receiver domain other.org appears in the generated reports (to= line parsed)"
else
    no "receiver domain not found in reports"
fi

# -------------------------------- 10: per-sender message size parsed from size=
# Only "from=" lines carry bytes into the accounting: parseSendmailToLine()
# calls checkUser(..., TO_MAIL, 0), so a to= line's size= field is ignored.
if grep -rq '1024.00 bytes' "$WORK/out"; then
    ok "alice's 1024-byte message shows up in the sender size table"
else
    no "per-sender size '1024.00 bytes' not found in reports"
fi

# --------------------------------------- 11: message sizes are summed, not echoed
# 512 (carol) + 1024 (alice) = 1536 -> isoqlog renders the aggregate as 1.50 KB.
if grep -rq '1\.50 KBytes' "$WORK/out"; then
    ok "byte accounting sums the senders: 512+1024 renders as 1.50 KBytes"
else
    no "expected aggregate 1.50 KBytes not found in reports"
fi

# ------------------------------ 12: a log line of another month is ignored (date gate)
# check_syslog_date() accepts a line only when its month abbreviation *and*
# day-of-month both equal today's.  The device date(1) supports neither
# "-d yesterday" nor "-v-1d", so instead of computing yesterday we stamp the
# line with a month that provably is not the current one - that rejects it for
# the same reason and stays correct on any day of the year.
FAKE_MONTH="Jun"
[ "$(date '+%b')" = "Jun" ] && FAKE_MONTH="Jul"
rm -rf "$WORK/out2"
mkdir -p "$WORK/out2"
printf '%s  5 10:00:01 mailhost sendmail[2234]: f8O0Y1vA002234: from=<zoe@yesterday.test>, size=999, class=0, nrcpts=1, proto=ESMTP, daemon=MTA, relay=localhost\n' \
    "$FAKE_MONTH" > "$WORK/othermonth.log"
sed -e "s#$WORK/mail.log#$WORK/othermonth.log#" -e "s#$WORK/out#$WORK/out2#" \
    "$WORK/isoqlog.conf" > "$WORK/other.conf"
"$BIN" -f "$WORK/other.conf" > "$WORK/other.out" 2>&1
rc=$?
if [ "$rc" != 0 ]; then
    no "run with an out-of-today log failed rc=$rc out=$(head -3 "$WORK/other.out")"
elif grep -rq 'zoe@yesterday.test' "$WORK/out2"; then
    no "a log line stamped $FAKE_MONTH (not $(date '+%b')) was counted - the date gate does not hold"
else
    ok "log lines outside today are ignored (check_syslog_date gate holds)"
fi

total=$((pass + failn))
if [ "$failn" != 0 ]; then
    printf 'ISOQLOG_TEST_ASSERTIONS pass=%d fail=%d\n' "$pass" "$failn"
    printf 'ISOQLOG_TEST_FAIL %d of %d assertion(s) failed\n' "$failn" "$total"
    exit 1
fi
printf 'ISOQLOG_TEST_ASSERTIONS pass=%d fail=%d\n' "$pass" "$failn"
printf 'ISOQLOG_TEST_PASS %d/%d assertions\n' "$pass" "$total"
exit 0
