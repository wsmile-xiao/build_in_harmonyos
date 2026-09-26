#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for recoverdm 0.20 (OHOS aarch64)
#
# Runs inside the conanrun environment, so the packaged bin/ is on PATH.
# R34: every assertion executes the *packaged* binaries; nothing is mocked.
# Each expected exit code / byte pattern was measured on the device against the
# same upstream code path before being asserted here (see notes.md, 五维账本).
#
# Coverage:
#   A. both packaged executables resolve from bin/ and are executable
#   B. recoverdm version banner (indirect proof that the Makefile -DVERSION
#      macro survives the recipe's make-variable handling)
#   C. recoverdm usage paths (-h, and the documented no-argument exit code)
#   D. a REAL recovery pass over a regular file (device type FILE == 1):
#      byte-identical image + the upstream "Done" marker
#   E. mergebad usage paths (-h banner, "at least 2 images" guard)
#   F. a REAL mergebad merge driven by bad-block map files
#
# Not covered (deliberately, with the reason in MANIFEST.yml `not_covered`):
#   raw disk / CD-ROM / DVD / floppy paths (-t 10..19, -r, -s) and the bad-sector
#   list produced by -l: they need genuinely damaged media or a root-owned loop
#   device, which the HarmonyOS PC build hosts do not provide.
#
# The final line prints "<A>/<A> assertions PASSED"; the number transcribed into
# PR body / notes.md / manifest.yaml comes from that reading (one source).

set -u

A=0        # assertions executed
PASSED=0   # assertions passed (run aborts on the first failure)

fail() { echo "FAIL (after $PASSED/$A): $1" >&2; exit 1; }

assert() { # assert <description> <shell fragment>
    A=$((A + 1))
    if eval "$2" >/dev/null 2>&1; then
        PASSED=$((PASSED + 1))
        echo "OK [$PASSED] $1"
    else
        fail "$1"
    fi
}

WORK="recoverdm-test-workdir"
assert "work dir for test artefacts is creatable (device /tmp is read-only)" \
    'rm -rf "$WORK" && mkdir -p "$WORK"'
cd "$WORK" || fail "cannot enter the work dir"

RB="$(command -v recoverdm)"
MB="$(command -v mergebad)"
assert "packaged recoverdm resolves on PATH (conanrun bin/)" 'test -n "$RB"'
assert "packaged mergebad resolves on PATH (conanrun bin/)" 'test -n "$MB"'
assert "recoverdm is executable" 'test -x "$RB"'
assert "mergebad is executable" 'test -x "$MB"'

# ---- B. recoverdm version banner ------------------------------------------
assert "recoverdm -V runs and exits 0" '"$RB" -V >v-out.txt 2>v-err.txt; [ $? -eq 0 ]'
assert "recoverdm -V prints the upstream banner with version 0.20" \
    'grep -q "^recoverdm v0\.20, (c) 2003-2004 by folkert@vanheusden\.com$" v-out.txt'

# ---- C. recoverdm usage paths ---------------------------------------------
assert "recoverdm -h exits 0" '"$RB" -h >h-out.txt 2>h-err.txt; [ $? -eq 0 ]'
assert "recoverdm -h writes the upstream usage line on stderr" \
    'grep -q "^Usage: recoverdm -t <type> -i <file/device-in> -o <fileout>" h-err.txt'
assert "bare recoverdm exits 255 (upstream argc==1 usage path)" \
    '"$RB" >/dev/null 2>&1; [ $? -eq 255 ]'

# ---- D. real recovery over a regular file (device type FILE == 1) ---------
assert "4096-byte readable test image created" \
    'head -c 4096 /dev/zero | tr "\0" "A" > in.bin; [ "$(wc -c < in.bin)" -eq 4096 ]'
assert "recoverdm -t 1 (regular file) recovery exits 0" \
    '"$RB" -t 1 -i in.bin -o out.bin >rec-log.txt 2>&1; [ $? -eq 0 ]'
assert "recovered image present with size 4096" \
    'test -f out.bin; [ "$(wc -c < out.bin)" -eq 4096 ]'
assert "recovered image is byte-identical to the fully readable input" \
    'cmp -s in.bin out.bin'
# Upstream prints the progress offsets separated by bare CR (measured: the log
# tail is "...\r4096\rDone\n"), so "Done" does not start a line until CR is
# normalised — hence the tr before grep.
assert "recovery log ends with the upstream Done marker" \
    'tr "\r" "\n" < rec-log.txt | grep -q "^Done$"'

# ---- E. mergebad usage paths ----------------------------------------------
assert "mergebad -h exits 0" '"$MB" -h >mb-h-out.txt 2>mb-h-err.txt; [ $? -eq 0 ]'
assert "mergebad -h prints the upstream banner with version 0.20" \
    'grep -q "^mergebad v0\.20, (c) 2004 by folkert@vanheusden\.com$" mb-h-out.txt'
assert "bare mergebad exits 10 (at-least-two-images guard)" \
    '"$MB" >/dev/null 2>mb-none.txt; [ $? -eq 10 ]'
assert "bare mergebad reports the 2-image requirement" \
    'grep -q "Not enough input-images selected" mb-none.txt'

# ---- F. real mergebad merge ------------------------------------------------
# imgA is declared damaged in [1024,1536); imgB is intact up to the 4096
# boundary, so the merge must yield A[0:1024) + B[1024:4096).
# imgB's map file deliberately starts *at* the image length: with a start beyond
# it, upstream computes n_bytes_to_copy without capping to the real file size and
# the copy then fails with exit 16 (measured on the device), so the boundary
# value is the well-formed encoding of "no bad block inside this image".
assert "two 4096-byte images and their bad-block map files created" \
    'head -c 4096 /dev/zero | tr "\0" "A" > imgA && head -c 4096 /dev/zero | tr "\0" "B" > imgB && printf "1024 512" > mapA && printf "4096 512" > mapB && [ -s imgA ] && [ -s imgB ] && [ -s mapA ] && [ -s mapB ]'
assert "mergebad two-image merge exits 0" \
    '"$MB" -i mapA imgA -i mapB imgB -o merged.bin -l samebad.txt >mb-log.txt 2>&1; [ $? -eq 0 ]'
assert "merged image size 4096" '[ "$(wc -c < merged.bin)" -eq 4096 ]'
assert "merged[0:1024) taken from image A (its good span)" \
    '[ "$(head -c 1024 merged.bin | tr -d "A" | wc -c)" -eq 0 ]'
assert "merged[1024:4096) taken from image B (spanning A's bad block)" \
    '[ "$(tail -c 3072 merged.bin | tr -d "B" | wc -c)" -eq 0 ]'

cd .. || fail "cannot leave the work dir"
assert "work dir cleaned up" 'rm -rf "$WORK"; [ ! -e "$WORK" ]'

[ "$A" -eq "$PASSED" ] || fail "assertion bookkeeping inconsistent"
echo "recoverdm 0.20 consumer test: $PASSED/$A assertions PASSED"
