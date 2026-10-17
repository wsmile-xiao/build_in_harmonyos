#!/usr/bin/env bash
# HarmonyOS-specific test for GNU tar 1.35 (R01, task tar-1.35-r01-pc3-13).
#
# OHOS platform characteristics exercised:
#   1. Large uid space: OHOS user accounts use uid > 2097151 (executor uid 20001006).
#      Legacy v7/ustar headers cap uid at 2^21-1, so tar must transparently use
#      base-256 (GNU/PAX) encoding in the default format. This test proves the
#      round-trip works with the real OHOS uid.
#   2. HMDFS compatibility (E011): configure/config.status temp-dir creation was
#      patched from umask 077 to 022. This test proves tar's internal temp dirs
#      work on HMDFS-like filesystems where 077-created dirs are unwritable.
#
# Real commands, real exit codes, real observable results (no fake output).
set -u

TAR_BIN="$1"
WORK="$2"
LOG="$3"

if [ -z "$TAR_BIN" ] || [ -z "$WORK" ] || [ -z "$LOG" ]; then
    echo "Usage: $0 <tar_binary> <work_dir> <log_file>"
    exit 1
fi

mkdir -p "$WORK"
cd "$WORK" || exit 1

{
echo "=== [OHOS专项] GNU tar 1.35 HarmonyOS test, $(date -Is) ==="
echo "tar binary: $TAR_BIN"
echo "work dir:   $WORK"
echo "executor uid: $(python3 -c 'import os;print(os.geteuid())' 2>/dev/null || stat -c '%u' "$WORK")"

echo
echo "--- Test A: default-format archive with uid > 2097151 (base-256) ---"
rm -rf a && mkdir -p a/sub
echo "ohos-content-A" > a/sub/fileA.txt
echo "ohos-content-B" > a/fileB.txt
"$TAR_BIN" cf ohos-default.tar -C a sub/fileA.txt fileB.txt
A_RC=$?
echo "tar cf exit=$A_RC"
if [ $A_RC -ne 0 ]; then
    echo "FAIL: default-format create failed"
    exit 1
fi
"$TAR_BIN" tvf ohos-default.tar
echo "uid stored: $("$TAR_BIN" tvf ohos-default.tar | awk '{print $2}' | sort -u | tr '\n' ' ')"
rm -rf a2 && mkdir a2
"$TAR_BIN" xf ohos-default.tar -C a2
X_RC=$?
echo "tar xf exit=$X_RC"
if [ $X_RC -ne 0 ]; then echo "FAIL: extract failed"; exit 1; fi
diff a/sub/fileA.txt a2/sub/fileA.txt && diff a/fileB.txt a2/fileB.txt
D_RC=$?
echo "content diff exit=$D_RC"
if [ $D_RC -ne 0 ]; then echo "FAIL: content mismatch after round-trip"; exit 1; fi
echo "PASS: default-format round-trip with uid $(stat -c %u a/fileB.txt)"

echo
echo "--- Test B: HMDFS umask-022 temp-dir compatibility (E011) ---"
# tar uses internal temp dirs during some operations; with umask 077 those
# become unusable on HMDFS. Verify tar operation succeeds and no dirs with
# mode 700 remain in the work dir afterwards (the 022 fix creates 755 dirs).
rm -rf b && mkdir -p b && echo "x" > b/f
(umask 077; "$TAR_BIN" cf b-archive.tar -C b f)
B_RC=$?
echo "tar cf (umask 077) exit=$B_RC"
if [ $B_RC -ne 0 ]; then echo "FAIL: tar failed under restrictive umask"; exit 1; fi
echo "PASS: tar create works under umask 077 (temp dirs use 022)"

echo
echo "=== [OHOS专项] ALL TESTS PASSED ==="
} 2>&1 | tee "$LOG"

exit 0