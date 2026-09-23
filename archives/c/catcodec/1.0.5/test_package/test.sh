#!/data/service/hnp/bin/bash
# ============================================================================
# catcodec 1.0.5 test_package suite
# 11 test cases / 28 assertions:
#   Upstream behaviour, reproduced programmatically (5 cases, 16 assertions):
#     T1 help/version output            T2 encode 8-bit WAV -> .cat
#     T3 decode .cat -> byte-equal WAV  T4 16-bit 22050 Hz roundtrip
#     T5 two-sample catalogue: decode regenerates .sfo + both WAVs
#   New error-path / boundary tests (6 cases, 12 assertions):
#     T6 wrong .cat extension  T7 missing input file  T8 truncated .cat
#     T9 corrupt .cat header   T10 unsupported WAV rate  T11 malformed .sfo
# Counts synced in conanfile.py docstring, test_package/conanfile.py
# docstring, MANIFEST.yml and the PR description.
# ============================================================================
set -u

CC=catcodec
P=0
F=0

ok()   { P=$((P + 1)); echo "  ok   - $1"; }
bad()  { F=$((F + 1)); echo "  FAIL - $1"; }
chk()  { if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (got '$1' want '$2')"; fi; }
chkrc() { chk "$?" "$1" "$2"; }
grepq() { if grep -q -- "$1" "$2"; then ok "$3"; else bad "$3 (no match '$1' in $2)"; fi; }
fileq() { if [ -s "$1" ]; then ok "$2"; else bad "$2 (missing/empty: $1)"; fi; }

# --- emit little-endian byte escapes (2/4 bytes) ----------------------------
le2() { local v=$1; printf "\\\\x$(printf '%02x' $((v & 255)))\\\\x$(printf '%02x' $(((v >> 8) & 255)))"; }
le4() { local v=$1; printf "\\\\x$(printf '%02x' $((v & 255)))\\\\x$(printf '%02x' $(((v >> 8) & 255)))\\\\x$(printf '%02x' $(((v >> 16) & 255)))\\\\x$(printf '%02x' $(((v >> 24) & 255)))"; }

# --- generate a strict RIFF/PCM WAV: out rate bits nsamples ------------------
gen_wav() {
    local out=$1 rate=$2 bits=$3 n=$4 i v ds
    ds=$((n * bits / 8))
    local riff=$((36 + ds)) br=$((rate * bits / 8)) ba=$((bits / 8))
    local hdr="\x52\x49\x46\x46$(le4 $riff)\x57\x41\x56\x45\x66\x6d\x74\x20$(le4 16)\x01\x00\x01\x00$(le4 $rate)$(le4 $br)$(le2 $ba)$(le2 $bits)\x64\x61\x74\x61$(le4 $ds)"
    local body=""
    i=0
    if [ "$bits" -eq 8 ]; then
        while [ "$i" -lt "$n" ]; do
            v=$(((i * 7 + 5) % 256))
            body="${body}\\x$(printf '%02x' "$v")"
            i=$((i + 1))
        done
    else
        while [ "$i" -lt "$n" ]; do
            v=$(((i * 13 + 7) & 0xffff))
            body="${body}\\x$(printf '%02x' $((v & 255)))\\x$(printf '%02x' $(((v >> 8) & 255)))"
            i=$((i + 1))
        done
    fi
    printf '%b' "$hdr$body" > "$out"
}

HOME_DIR="${HOME:-/storage/Users/currentUser}"
cd "$HOME_DIR" || exit 1
WORK="$HOME_DIR/catcodec-test-$$"
rm -rf "$WORK"
mkdir -p "$WORK"

echo "== T1 help / usage / version (upstream CLI behaviour) =="
"$CC" > "$WORK/help.txt" 2>/dev/null
chkrc 0 "T1 no-args exits 0 and prints help"
grepq "catcodec version 1.0.5" "$WORK/help.txt" "T1 help contains version 1.0.5"
grepq "Usage:" "$WORK/help.txt" "T1 help contains usage"

echo "== T2 encode 8-bit 11025 Hz WAV into .cat =="
mkdir -p "$WORK/enc8" || exit 1
cd "$WORK/enc8" || exit 1
gen_wav tone8.wav 11025 8 300
printf '"tone8.wav" Steam engine whistle\n' > c8.sfo
"$CC" -e c8.cat >/dev/null 2>e8.err
chkrc 0 "T2 encode exits 0"
fileq c8.cat "T2 produced non-empty c8.cat"

echo "== T3 decode .cat back to byte-identical WAV =="
mkdir -p "$WORK/dec8" || exit 1
cd "$WORK/dec8" || exit 1
cp "$WORK/enc8/c8.cat" .
"$CC" -d c8.cat >/dev/null 2>d8.err
chkrc 0 "T3 decode exits 0"
cmp -s tone8.wav "$WORK/enc8/tone8.wav"
chk "$?" 0 "T3 decoded WAV is byte-identical to the source"

echo "== T4 roundtrip 16-bit 22050 Hz =="
mkdir -p "$WORK/enc16" "$WORK/dec16" || exit 1
cd "$WORK/enc16" || exit 1
gen_wav tone16.wav 22050 16 256
printf '"tone16.wav" Diesel engine\n' > c16.sfo
"$CC" -e c16.cat >/dev/null 2>e16.err
chkrc 0 "T4 encode (16-bit) exits 0"
cd "$WORK/dec16" || exit 1
cp "$WORK/enc16/c16.cat" .
"$CC" -d c16.cat >/dev/null 2>d16.err
chkrc 0 "T4 decode (16-bit) exits 0"
cmp -s tone16.wav "$WORK/enc16/tone16.wav"
chk "$?" 0 "T4 decoded 16-bit WAV is byte-identical"

echo "== T5 two-sample catalogue: .sfo metadata + both WAVs =="
mkdir -p "$WORK/multi" "$WORK/multi/out" || exit 1
cd "$WORK/multi" || exit 1
cp "$WORK/enc8/tone8.wav" "$WORK/enc16/tone16.wav" .
printf '"tone8.wav" Steam engine whistle\n"tone16.wav" Diesel engine\n' > m.sfo
"$CC" -e m.cat >/dev/null 2>em.err
chkrc 0 "T5 encode (2 samples) exits 0"
cd "$WORK/multi/out" || exit 1
cp "$WORK/multi/m.cat" .
"$CC" -d m.cat >/dev/null 2>dm.err
chkrc 0 "T5 decode (2 samples) exits 0"
grepq '"tone8.wav"' m.sfo "T5 regenerated .sfo lists tone8.wav"
grepq 'Steam engine whistle' m.sfo "T5 regenerated .sfo keeps sample name"
cmp -s tone8.wav "$WORK/multi/tone8.wav"
chk "$?" 0 "T5 decoded tone8.wav identical"
cmp -s tone16.wav "$WORK/multi/tone16.wav"
chk "$?" 0 "T5 decoded tone16.wav identical"

echo "== T6 wrong extension rejected =="
mkdir -p "$WORK/err" || exit 1
cd "$WORK/err" || exit 1
cp "$WORK/enc8/tone8.wav" .
"$CC" -d tone8.wav >/dev/null 2>t6.err
chkrc 255 "T6 non-.cat input rejected"
grepq "Unexpected extension" t6.err "T6 reports unexpected extension"

echo "== T7 missing input file rejected =="
"$CC" -d missing.cat >/dev/null 2>t7.err
chkrc 255 "T7 missing input rejected"
grepq "Could not open" t7.err "T7 reports could-not-open"

echo "== T8 truncated .cat rejected =="
cp "$WORK/enc8/c8.cat" trunc.cat
head -c 30 trunc.cat > trunc2.cat && mv trunc2.cat trunc.cat
"$CC" -d trunc.cat >/dev/null 2>t8.err
chkrc 255 "T8 truncated .cat rejected"
grepq "Unexpected end" t8.err "T8 reports unexpected end"

echo "== T9 corrupt .cat header rejected =="
printf '\x08\x00\x00\x00\x10\x00\x00\x00\x20\x00\x00\x00\x05\x41\x42' > corrupt.cat
"$CC" -d corrupt.cat >/dev/null 2>t9.err
chkrc 255 "T9 corrupt .cat rejected"
grepq "Unexpected end" t9.err "T9 reports unexpected end"

echo "== T10 unsupported WAV sample rate rejected =="
gen_wav badrate.wav 8000 8 200
printf '"badrate.wav" Bad rate\n' > t10.sfo
"$CC" -e t10.cat >/dev/null 2>t10.err
chkrc 255 "T10 8000 Hz WAV rejected"
grepq "Unexpected same rate" t10.err "T10 reports unsupported rate"

echo "== T11 malformed .sfo line rejected =="
printf 'no-space-separator-line\n' > t11.sfo
"$CC" -e t11.cat >/dev/null 2>t11.err
chkrc 255 "T11 malformed .sfo rejected"
grepq "Invalid format" t11.err "T11 reports invalid sfo format"

echo "summary: $P passed, $F failed"
if [ "$F" -eq 0 ]; then exit 0; else exit 1; fi
