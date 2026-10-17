#!/data/service/hnp/bin/bash
# test_package/test.sh — functional test for the zpaq 0.01 archiver
# Runs in conanrun env (PATH includes installed bin/)
# R34: genuinely exercises the tested package's binary —
# compress → list → extract roundtrip with byte-exact verification.
#
# Upstream storage semantics: zpaq stores and restores file names
# exactly as given on the command line, and extracts relative to the
# current working directory (it never creates directories itself), so
# the test compresses RELATIVE paths and extracts from a subdirectory.
set -euo pipefail

# Locate the packaged min.cfg (upstream fast order-4 model).
CFG=""
for d in "${CONAN_LIBZPAQ_CFG_DIR:-}" \
         "$(dirname "$(command -v zpaq)")/../share/libzpaq" \
         ../share/libzpaq; do
    if [ -f "$d/min.cfg" ]; then CFG="$d/min.cfg"; break; fi
done

if [ -z "$CFG" ]; then
    # Fallback: inline copy of the upstream min.cfg model
    # (order-4 context model, 4 MB memory — verbatim from the 0.01 tag)
    CFG="$(mktemp "${TMPDIR:-/data/storage/el2/base/temp}/mincfg.XXXXXX")"
    cat > "$CFG" <<'EOF'
comp 0 0 0 0 1
  0 cm 20 12
hcomp
  *d<>a a+=*d a*=192 *d=a
  halt
post
  pass
end
EOF
    # Only the self-created temp file may be removed by the EXIT trap;
    # the packaged share/libzpaq/min.cfg must never be deleted.
    TMPCFG="$CFG"
    echo "[test] packaged min.cfg not found, using inline upstream copy"
fi
echo "[test] model config: $CFG"

WORK="$(mktemp -d "${TMPDIR:-/data/storage/el2/base/temp}/zpaq-test.XXXXXX")"
trap 'rm -rf "$WORK" 2>/dev/null; [ -n "${TMPCFG:-}" ] && rm -f "$TMPCFG" 2>/dev/null || true' EXIT

# Test input: three files with different content characteristics
# (random binary / repetitive numbers / short text)
mkdir -p "$WORK/src/sub"
head -c 2048 /dev/urandom > "$WORK/src/rand.bin"
seq 1 300 > "$WORK/src/num.txt"
printf 'hello zpaq on OHOS!\n' > "$WORK/src/sub/msg.txt"

echo "[test] 1. compression (relative paths, cwd=$WORK)"
cd "$WORK"
zpaq "c$CFG" test.zpaq src/rand.bin src/num.txt src/sub/msg.txt > compress.log 2>&1 || { cat compress.log; exit 1; }
grep -q "rand.bin" compress.log || { echo "FAIL: compression log missing rand.bin"; cat compress.log; exit 1; }
test -s test.zpaq || { echo "FAIL: archive is empty"; exit 1; }
echo "OK: archive created ($(stat -c%s test.zpaq) bytes)"

echo "[test] 2. list archive"
zpaq l test.zpaq > list.log 2>&1
grep -q "rand.bin" list.log || { echo "FAIL: list missing rand.bin"; cat list.log; exit 1; }
grep -q "num.txt" list.log || { echo "FAIL: list missing num.txt"; exit 1; }
grep -q "msg.txt" list.log || { echo "FAIL: list missing msg.txt"; exit 1; }
echo "OK: all 3 files listed"

echo "[test] 3. extract and verify roundtrip"
# zpaq does not create directories itself (upstream readme documents this)
mkdir -p out/src/sub
cd out
zpaq x ../test.zpaq > extract.log 2>&1 || { cat extract.log; exit 1; }
cmp src/rand.bin ../src/rand.bin || { echo "FAIL: rand.bin differs"; exit 1; }
cmp src/num.txt ../src/num.txt || { echo "FAIL: num.txt differs"; exit 1; }
cmp src/sub/msg.txt ../src/sub/msg.txt || { echo "FAIL: msg.txt differs"; exit 1; }
echo "OK: all 3 files byte-exact roundtrip"

echo "[test] 4. smoke: unknown option prints usage and exits 0"
zpaq --version > ../ver.log 2>&1
grep -q "Usage: zpaq" ../ver.log || { echo "FAIL: usage banner missing"; cat ../ver.log; exit 1; }
echo "OK: usage banner printed"

echo ""
echo "ALL TESTS PASSED"
