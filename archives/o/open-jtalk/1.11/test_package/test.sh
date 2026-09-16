#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the packaged open_jtalk 1.11
#
# Runs in the conanrun environment, so PATH already contains the packaged
# bin/ directory of the tested reference.
set -euo pipefail

fail() { echo "FAIL: $*" >&2; exit 1; }
pass() { echo "PASS: $*"; }

BIN="$(command -v open_jtalk || true)"
[ -n "$BIN" ] || fail "open_jtalk is not on PATH inside the conanrun environment"
PKG_ROOT="$(cd "$(dirname "$BIN")/.." && pwd)"
DIC="$PKG_ROOT/dic"
echo "[test] binary=$BIN  dic=$DIC"

# ── 1) the delivered artifact is the OHOS aarch64 executable ────────────────
magic="$(head -c 4 "$BIN" | od -An -tx1 | tr -d ' \n')"
[ "$magic" = "7f454c46" ] || fail "$BIN is not an ELF file (magic=$magic)"
if command -v readelf >/dev/null 2>&1; then
    readelf -h "$BIN" | grep -q 'AArch64' || fail "$BIN is not an AArch64 ELF"
fi
pass "delivered artifact is the AArch64 ELF binary ($(stat -c %s "$BIN") bytes)"

# ── 2) the CLI actually runs ────────────────────────────────────────────────
usage="$(open_jtalk -h 2>&1)" || fail "open_jtalk -h returned a non-zero exit code"
grep -q 'Open JTalk' <<<"$usage" || fail "-h output lacks the Open JTalk banner"
# HTS_COPYRIGHT is a macro from hts_engine_API's HTS_engine.h, so this banner can
# only appear if the privately built hts_engine_API 1.10 headers were compiled in
# (note: open_jtalk.c hard-codes its own "Version 1.10" line, which would NOT
# prove anything about the dependency).
grep -q 'The HMM-Based Speech Synthesis Engine "hts_engine API"' <<<"$usage" \
    || fail "-h output lacks the hts_engine_API banner"
pass "open_jtalk -h prints the Open JTalk banner plus the hts_engine_API 1.10 banner"

# ── 3) the bundled NAIST-JDic dictionary was installed ─────────────────────
for f in sys.dic matrix.bin char.bin unk.dic left-id.def rewrite.def pos-id.def right-id.def; do
    [ -s "$DIC/$f" ] || fail "dictionary file $DIC/$f is missing or empty"
done
dic_size="$(stat -c %s "$DIC/sys.dic")"
[ "$dic_size" -gt 50000000 ] || fail "sys.dic is unexpectedly small ($dic_size bytes)"
pass "bundled dictionary installed (sys.dic=$dic_size bytes)"

# ── 4) the packaged dictionary really loads ────────────────────────────────
# Open_JTalk_load() runs Mecab_load(dic) *before* HTS_Engine_load(voice), and
# returns early if the dictionary fails. Upstream ships no .htsvoice model in
# the source tarball, so pointing -m at a missing file is the deepest reachable
# assertion: reaching HTS_fopen proves Mecab_load() already succeeded on the
# packaged dic/, and the documented exit 1 is the upstream behaviour.
set +e
msg="$(printf 'こんにちは\n' | open_jtalk -x "$DIC" -m "$DIC/__no_voice__.htsvoice" 2>&1)"
rc=$?
set -e
[ "$rc" -eq 1 ] || fail "expected exit code 1 without an HTS voice model, got $rc: $msg"
grep -q '^Warning: HTS_fopen: Cannot open' <<<"$msg" \
    || fail "dictionary was not loaded before the voice model: $msg"
grep -q 'cannot be loaded' <<<"$msg" || fail "unexpected failure message: $msg"
pass "packaged dic/ loaded by Mecab_load (reached the voice-model stage)"

echo "ALL OPEN_JTALK CONSUMER TESTS PASSED"
