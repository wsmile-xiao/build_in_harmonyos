#!/bin/sh
# Consumer test for the mairix CLI: index a synthetic maildir, then
# search it and verify matches are symlinked into the output folder.
# $1 = package bin dir.
set -e

BINDIR="$1"
MAIRIX="${BINDIR:+$BINDIR/}mairix"

work="${TMPDIR:-.}/mairix_test.$$"
mkdir -p "$work"
cd "$work"

fail() { echo "FAIL: $1"; exit 1; }

# 1. version probe
out=$("$MAIRIX" -V 2>&1)
echo "$out" | grep -q "mairix" || fail "-V did not print program name"

# 2. synthetic maildir: two senders
mkdir -p mdir/cur mdir/new mdir/tmp
printf 'From: alice@example.com\nTo: bob@example.com\nSubject: meeting notes\nDate: Mon, 21 Sep 2026 10:00:00 +0800\n\nlunch tomorrow\n' > mdir/cur/msg1
printf 'From: carol@example.com\nTo: bob@example.com\nSubject: quarterly report\nDate: Mon, 21 Sep 2026 11:00:00 +0800\n\nreport attached\n' > mdir/cur/msg2

# 3. rc file and index build (base= is mandatory; folder paths are
# relative to it — same shape the upstream test suite generates)
mkdir -p results/cur results/new results/tmp
cat > mairixrc <<EOF
database=$work/database
base=$work
maildir=mdir
mfolder=results
EOF
"$MAIRIX" -f mairixrc || fail "indexing failed"
[ -e "$work/database" ] || fail "database file not created"

# 4. search: exactly alice's message is linked into the results folder
"$MAIRIX" -f mairixrc f:alice || fail "search failed"
n=$(find results -type l 2>/dev/null | wc -l)
[ "$n" -eq 1 ] || fail "expected 1 match for f:alice, got $n"

# 5. non-matching search leaves the results folder empty
# (mairix exits 1 when a search has no matches — acceptable here)
rc=0
"$MAIRIX" -f mairixrc f:doesnotexist || rc=$?
[ "$rc" -le 1 ] || fail "negative search exited $rc"
n=$(find results -type l 2>/dev/null | wc -l)
[ "$n" -eq 0 ] || fail "expected 0 matches for f:doesnotexist, got $n"

echo "mairix consumer test: PASS"
