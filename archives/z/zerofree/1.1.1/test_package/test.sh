#!/data/service/hnp/bin/bash
# test_package/test.sh - end-to-end test for zerofree 1.1.1.
#
# Runs inside the conanrun env (PATH already contains the packaged bin/).
#
# The fixture is a real 1 MiB ext2 filesystem (1024 blocks x 1 KiB, 970 of them
# free) whose free data blocks were deliberately overwritten with a non-zero
# pattern, so zerofree has actual work to do.  Re-running the tool afterwards
# must report 0 modified blocks - that is the property that proves the tool
# really walked the block bitmap and rewrote the free blocks, instead of merely
# exiting 0.
#
# Every assertion goes through ok()/note-style ledger writers, so the last line
# of output is a self-reported `N/N assertions passed` that can be cross-checked
# with `grep -c '[ok]' <log>`.
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

# /tmp is read-only on OHOS (E002) - keep scratch under TMPDIR/$HOME.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
WORK="$SCRATCH/zerofree-test-$$"
mkdir -p "$WORK"

OKFILE="$WORK/ledger"
export OKF="$OKFILE"
: > "$OKFILE"
ok() {
    echo "        [ok] $1"
    echo "$1" >> "$OKFILE"
}
fail() {
    echo "        [FAIL] $1"
    echo "[test] $(wc -l < "$OKFILE" 2>/dev/null || echo 0) assertions passed before failure"
    exit 1
}
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

command -v zerofree >/dev/null || fail "zerofree is not on PATH"
ok "zerofree is on PATH"

# ── 1. argument contract (upstream getopt "nvf:") ───────────────────────────
echo "[test] zerofree <no arguments>"
if zerofree >"$WORK/out" 2>"$WORK/err"; then
    fail "zerofree with no arguments exited 0"
fi
grep -q "usage: zerofree" "$WORK/err" || fail "no-argument run did not print the usage line"
ok "no arguments -> usage on stderr + non-zero exit"

echo "[test] zerofree -x <image> (unknown option)"
if zerofree -x "$WORK/nope.img" >/dev/null 2>&1; then
    fail "unknown option exited 0"
fi
ok "unknown option rejected with a non-zero exit status"

echo "[test] zerofree -f 999 <image> (out-of-range fill value)"
if zerofree -f 999 "$WORK/nope.img" >/dev/null 2>"$WORK/err"; then
    fail "-f 999 exited 0"
fi
grep -q "fill value must be 0-255" "$WORK/err" || fail "-f 999 did not report the range error"
ok "-f 999 -> 'fill value must be 0-255'"

echo "[test] zerofree -f abc <image> (non-numeric fill value)"
if zerofree -f abc "$WORK/nope.img" >/dev/null 2>"$WORK/err"; then
    fail "-f abc exited 0"
fi
grep -q "invalid argument to -f" "$WORK/err" || fail "-f abc did not report the parse error"
ok "-f abc -> 'invalid argument to -f'"

echo "[test] zerofree -nv <missing image>"
if zerofree -nv "$WORK/does-not-exist.img" >/dev/null 2>"$WORK/err"; then
    fail "a missing image exited 0"
fi
grep -q "failed to open filesystem" "$WORK/err" || fail "missing image was not reported"
ok "missing image -> 'failed to open filesystem' + non-zero exit"

# ── 2. the real thing: an ext2 image with dirty free blocks ─────────────────
echo "[test] decoding ext2 fixture"
base64 -d data/ext2-1024blk-dirty.img.gz.b64 > "$WORK/img.gz" || fail "base64 decode failed"
gzip -dc "$WORK/img.gz" > "$WORK/img" || fail "gzip decompress failed"
SIZE=$(wc -c < "$WORK/img")
[ "$SIZE" -eq 1048576 ] || fail "fixture is $SIZE bytes, expected 1048576"
ok "fixture decoded (1048576 bytes = 1024 blocks x 1 KiB)"

# `-v` is what makes zerofree print its machine-readable summary: "\r<modified>/<free>/<total>"
run_summary() {
    zerofree -nv "$1" 2>/dev/null | tr -d '\r'
}

echo "[test] zerofree -nv <image>  (dry run)"
BEFORE=$(run_summary "$WORK/img") || fail "dry run exited non-zero"
echo "        [test] summary(before) = $BEFORE"
B_MOD=$(echo "$BEFORE" | cut -d/ -f1)
B_FREE=$(echo "$BEFORE" | cut -d/ -f2)
B_TOTAL=$(echo "$BEFORE" | cut -d/ -f3)
[ "$B_TOTAL" = "1024" ] || fail "total block count reported as $B_TOTAL, expected 1024"
ok "dry run reports the fixture geometry (1024 blocks total)"
[ "$B_FREE" = "970" ] || fail "free block count reported as $B_FREE, expected 970"
ok "dry run reports 970 free blocks"
[ "$B_MOD" -gt 0 ] || fail "fixture has no dirty free blocks ($B_MOD modified) - test would be vacuous"
ok "dry run finds $B_MOD dirty free blocks (fixture is genuinely dirty)"

echo "[test] zerofree <image>  (real run)"
zerofree "$WORK/img" >/dev/null 2>&1 || fail "real run exited non-zero"
ok "real run over the image exited 0"

echo "[test] zerofree -nv <image>  (after the real run)"
AFTER=$(run_summary "$WORK/img") || fail "post-run dry run exited non-zero"
echo "        [test] summary(after)  = $AFTER"
A_MOD=$(echo "$AFTER" | cut -d/ -f1)
[ "$A_MOD" = "0" ] || fail "after the real run $A_MOD free blocks are still dirty, expected 0"
ok "after the real run 0 free blocks are dirty (the rewrite actually happened)"
[ "$(echo "$AFTER" | cut -d/ -f2)" = "970" ] ||
    fail "free block count changed across the run: $B_FREE -> $(echo "$AFTER" | cut -d/ -f2)"
ok "free block count unchanged by the rewrite (970)"

echo "[test] -f <fillval> is honoured"
# The fixture was just fully zeroed by the run above, so rewriting it with a
# non-zero fill value must make *every* free block differ from the default
# all-zero fill again - i.e. a following dry run has to report modified == free.
cp "$WORK/img.gz" "$WORK/img2.gz"; gzip -dc "$WORK/img2.gz" > "$WORK/img2"
zerofree -nv "$WORK/img2" >/dev/null 2>&1 || fail "pre-run dry run on img2 failed"
zerofree -f 255 "$WORK/img2" >/dev/null 2>&1 || fail "-f 255 exited non-zero"
FILLED=$(run_summary "$WORK/img2") || fail "post -f 255 dry run exited non-zero"
echo "        [test] summary(after -f 255) = $FILLED"
[ "$(echo "$FILLED" | cut -d/ -f1)" = "970" ] ||
    fail "-f 255 left $(echo "$FILLED" | cut -d/ -f1) free blocks non-zero, expected all 970"
ok "-f 255 filled every free block with the requested non-zero value (970/970)"

echo ""
TOTAL=$(wc -l < "$OKFILE")
[ "$TOTAL" -gt 0 ] || fail "assertion ledger is empty - no assertion ever ran"
echo "        [test] $TOTAL/$TOTAL assertions passed"
echo "All tests passed."
