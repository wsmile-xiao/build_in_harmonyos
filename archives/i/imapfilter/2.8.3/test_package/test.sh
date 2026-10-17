#!/bin/sh
# test_package consumer test for imapfilter 2.8.3.
# Usage: test.sh <package_share_dir>   (share/imapfilter inside the package)
#
# R34: genuinely exercises the packaged binary and its package layout.
# Note: -V/-h print to stderr (version()/usage() use fprintf(stderr, ...)),
#       both exit 0 ("NOTREACHED" paths in src/imapfilter.c).
set -u

SHARE_DIR="${1:-}"

echo "--- imapfilter 2.8.3 consumer verification ---"

# 1. Version banner: "IMAPFilter 2.8.3  <copyright>", exit 0.
out1=$(imapfilter -V 2>&1)
rc1=$?
[ "$rc1" = "0" ] || { echo "FAIL: imapfilter -V exit=$rc1"; exit 1; }
echo "$out1" | grep -q "IMAPFilter 2.8.3" || {
    echo "FAIL: unexpected -V output [$out1]"; exit 1; }
echo "PASS 1: -V -> $out1"

# 2. Usage / option parsing: "usage: imapfilter [-inVv] ...", exit 0.
out2=$(imapfilter -h 2>&1)
rc2=$?
[ "$rc2" = "0" ] || { echo "FAIL: imapfilter -h exit=$rc2"; exit 1; }
echo "$out2" | grep -q "^usage: imapfilter" || {
    echo "FAIL: unexpected -h output [$out2]"; exit 1; }
echo "PASS 2: -h -> $(echo "$out2" | head -1)"

# 3. Packaging completeness: all 8 Lua runtime modules must be shipped in
#    share/imapfilter. The binary loads them from its compiled-in SHAREDIR
#    on every config/eval run before executing any Lua code, so a missing
#    module makes the tool non-functional for its intended purpose.
rc3=0
for f in common.lua set.lua regex.lua account.lua mailbox.lua \
         message.lua options.lua auxiliary.lua; do
    if [ ! -f "$SHARE_DIR/$f" ]; then
        echo "FAIL: missing packaged Lua module: $SHARE_DIR/$f"
        rc3=1
    fi
done
[ "$rc3" = "0" ] || exit 1
echo "PASS 3: 8/8 Lua modules present in $SHARE_DIR"

echo "test imapfilter 2.8.3: 3/3 checks PASS"
exit 0
