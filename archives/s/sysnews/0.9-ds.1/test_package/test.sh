#!/usr/bin/env bash
# Consumer test for the packaged `news` binary (runs in conanrun env).
# Builds a news directory with real files, then exercises the options whose
# behaviour depends on the platform: per-user $HOME/.news_time tracking,
# mtime-based expiry (unlink), getpwuid owner lookup and exit codes.
set -eu
CHECK="$1"
T="$(mktemp -d)"
trap 'rm -rf "$T"' EXIT
export HOME="$T/home"
D="$T/news"
mkdir -p "$HOME" "$D"

printf 'hello world\n' > "$D/welcome"
printf 'maintenance window\n' > "$D/maint"
printf 'old notice\n' > "$D/stale"
touch -t 200001010000 "$D/stale"

echo "[1] --version"
news --version | grep -q 'news version 0.9'

echo "[2] -s counts all articles newer than last read (no stamp yet => all 3)"
news -f "$D" -s | grep -qx 'NEWS: 3 news articles'

echo "[3] -n -l lists names, consumed by C checker"
news -f "$D" -n -l | "$CHECK" 3 welcome maint stale

echo "[4] -d adds strftime datestamp"
news -f "$D" -n -l -d -D '%Y' | grep -q 'NEWS: [0-9][0-9][0-9][0-9] '

echo "[5] -a prints article body with header"
out="$(news -f "$D" -a welcome)"
echo "$out" | grep -q '^\*\* welcome ('
echo "$out" | grep -q 'hello world'

echo "[6] article name filter"
news -f "$D" -n -l maint | "$CHECK" 1 maint

echo "[7] first plain run creates \$HOME/.news_time, second run sees nothing new"
news -f "$D" > /dev/null
test -f "$HOME/.news_time"
rc=0; news -f "$D" > /dev/null || rc=$?
test "$rc" -eq 2

echo "[8] -e 30 expires only articles older than 30 days"
news -f "$D" -e 30 -v | grep -qx 'Expiring article: stale'
test ! -e "$D/stale"
test -f "$D/welcome" && test -f "$D/maint"
news -f "$D" -a -n -l | "$CHECK" 2 welcome maint

echo "[9] unreadable newsdir => non-zero exit"
if news -f "$T/missing" -s 2> /dev/null; then echo "FAIL: missing dir accepted"; exit 1; fi

echo "ALL PASS"
