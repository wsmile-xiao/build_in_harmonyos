#!/data/service/hnp/bin/bash
# ============================================================================
# unalz 0.65 test_package suite
# 9 test cases / 28 assertions:
#   Upstream behaviour, reproduced programmatically (6 cases, 17 assertions):
#     T1 no-args banner (upstream version probe)   T2 extraction of a stored ALZ
#     T3 -l listing                                T4 -p pipe extraction
#     T5 selective extraction by filename          T6 missing-input error text
#   New OHOS-side tests (3 cases, 7 assertions):
#     T7 -v/--version/-h/--help switches (portability patch)
#     T8 EUC-KR -> UTF-8 filename conversion (musl iconv)
#     T9 corrupt-archive error text
# Counts synced in conanfile.py docstring, test_package/conanfile.py
# docstring, MANIFEST.yml and the PR description.
#
# NOTE: upstream unalz returns 0 on every error path (it prints an error
# message instead) — error-path assertions therefore check the output text,
# and the rc==0 quirk is asserted explicitly, not papered over.
#
# Fixture: a minimal valid ALZ archive is generated at runtime (a committed
# .alz binary would violate the no-archives rule). Layout mirrors the
# on-disk structures parsed by UnAlz.cpp: "ALZ\x01" global header, "BLZ\x01"
# local file header (fileDescriptor 0x40 = 4-byte size fields, compression
# method 0 = stored, CRC32), "CLZ\x01" central directory, "CLZ\x02" EOCD.
# ============================================================================
set -u

CC=unalz
P=0
F=0

ok()   { P=$((P + 1)); echo "  ok   - $1"; }
bad()  { F=$((F + 1)); echo "  FAIL - $1"; }
chk()  { if [ "$1" = "$2" ]; then ok "$3"; else bad "$3 (got '$1' want '$2')"; fi; }
grepq() { if printf '%s' "$2" | grep -q -- "$1"; then ok "$3"; else bad "$3 (no match '$1')"; fi; }
fileq() { if [ -s "$1" ]; then ok "$2"; else bad "$2 (missing/empty: $1)"; fi; }

# NOTE: /tmp is read-only on OHOS — use the workspace scratch dir.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/unalz-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# --- generate a minimal stored ALZ: out file, then name/filepath pairs ------
gen_alz() {
    python3 - "$@" <<'PYEOF'
import struct, sys, zlib

def le16(v): return struct.pack('<H', v)
def le32(v): return struct.pack('<I', v)

out_path = sys.argv[1]
entries = []
for i in range(2, len(sys.argv), 2):
    entries.append((sys.argv[i].encode('utf-8'), sys.argv[i + 1].encode('utf-8')))

blob = b""
for name, content in entries:
    # EUC-KR filenames are embedded raw for the -utf8 conversion test
    name_enc = name.decode('utf-8').encode('euc-kr')
    crc = zlib.crc32(content) & 0xffffffff
    blob += b"ALZ\x01" + le32(0)                    # SIG_ALZ_FILE_HEADER + SAlzHeader.unknown
    blob += b"BLZ\x01"                              # SIG_LOCAL_FILE_HEADER
    blob += le16(len(name_enc)) + b"\x20"           # fileNameLength, fileAttribute=FILE
    blob += le32(0x4C5A0000)                        # fileTimeDate (DOS time, value unused here)
    blob += b"\x40" + b"\x00"                       # fileDescriptor=0x40 (4-byte sizes), unknown2
    blob += b"\x00" + b"\x00"                       # compressionMethod=0 (stored), unknown
    blob += le32(crc) + le32(len(content)) + le32(len(content))
    blob += name_enc + content
blob += b"CLZ\x01" + le32(0) + le32(0) + b"CLZ\x03"  # central directory (12-byte head)
blob += b"CLZ\x02"                                   # end of central directory

with open(out_path, "wb") as f:
    f.write(blob)
PYEOF
}

KR_NAME="테스트.txt"     # extracted name must come back as UTF-8 via iconv

gen_alz "$TESTDIR/basic.alz" "hello.txt" "Hello ALZ!
"
gen_alz "$TESTDIR/kr.alz" "$KR_NAME" "Korean filename content
"
gen_alz "$TESTDIR/two.alz" "a.txt" "AAA
" "b.txt" "BBB
"

# --- T1: no-args banner (upstream version probe, rc=0) ----------------------
echo "# T1 no-args banner"
OUT=$("$CC" 2>&1); rc=$?
chk "$rc" 0 "T1: unalz with no arguments exits 0"
grepq "unalz v0.65" "$OUT" "T1: banner shows unalz v0.65"

# --- T2: extraction of a stored ALZ -----------------------------------------
echo "# T2 extract stored member"
mkdir -p "$TESTDIR/out2"
OUT=$("$CC" -d "$TESTDIR/out2" "$TESTDIR/basic.alz" 2>&1); rc=$?
chk "$rc" 0 "T2: unalz -d extracts basic.alz with rc=0"
fileq "$TESTDIR/out2/hello.txt" "T2: hello.txt extracted non-empty"
if cmp -s "$TESTDIR/out2/hello.txt" <(printf 'Hello ALZ!\n'); then
    ok "T2: extracted content byte-equal"
else
    bad "T2: extracted content byte-equal"
fi
grepq "done." "$OUT" "T2: extraction reports done"

# --- T3: -l listing ----------------------------------------------------------
echo "# T3 list mode"
OUT=$("$CC" -l "$TESTDIR/basic.alz" 2>&1); rc=$?
chk "$rc" 0 "T3: unalz -l exits 0"
grepq "Listing archive" "$OUT" "T3: listing header printed"
grepq "hello.txt" "$OUT" "T3: member name listed"
grepq "Total 1 file" "$OUT" "T3: total count listed"

# --- T4: -p pipe extraction ---------------------------------------------------
echo "# T4 pipe extraction"
OUT=$("$CC" -p "$TESTDIR/basic.alz" 2>/dev/null); rc=$?
if [ "$OUT" = "Hello ALZ!" ]; then
    ok "T4: -p writes member content to stdout"
else
    bad "T4: -p writes member content to stdout (got '$OUT')"
fi
chk "$rc" 0 "T4: -p mode exits 0"

# --- T5: selective extraction by member name ---------------------------------
echo "# T5 selective extraction"
mkdir -p "$TESTDIR/out5"
OUT=$("$CC" -d "$TESTDIR/out5" "$TESTDIR/two.alz" b.txt 2>&1); rc=$?
chk "$rc" 0 "T5: extracting named member b.txt exits 0"
fileq "$TESTDIR/out5/b.txt" "T5: b.txt extracted"
if [ ! -e "$TESTDIR/out5/a.txt" ]; then
    ok "T5: a.txt not extracted when b.txt selected"
else
    bad "T5: a.txt not extracted when b.txt selected"
fi
if cmp -s "$TESTDIR/out5/b.txt" <(printf 'BBB\n'); then
    ok "T5: b.txt content byte-equal"
else
    bad "T5: b.txt content byte-equal"
fi

# --- T6: missing-input error text (upstream returns 0 even on error) ---------
echo "# T6 missing input"
OUT=$("$CC" -l "$TESTDIR/definitely-missing.alz" 2>&1); rc=$?
chk "$rc" 0 "T6: upstream quirk — missing input still exits 0"
grepq "file open error" "$OUT" "T6: missing input reports file open error"

# --- T7: -v/--version/-h/--help switches (portability patch) ------------------
echo "# T7 version/help switches"
OUT=$("$CC" --version 2>&1); rc=$?
chk "$rc" 0 "T7: --version exits 0"
grepq "unalz v0.65" "$OUT" "T7: --version prints version banner"
OUT=$("$CC" -h 2>&1); rc=$?
chk "$rc" 0 "T7: -h exits 0"
grepq "Usage : unalz" "$OUT" "T7: -h prints usage"
OUT=$("$CC" -v 2>&1); rc=$?
grepq "unalz v0.65" "$OUT" "T7: -v prints version banner"

# --- T8: EUC-KR -> UTF-8 filename conversion (musl iconv) ---------------------
echo "# T8 filename codepage conversion"
mkdir -p "$TESTDIR/out8"
OUT=$("$CC" -utf8 -d "$TESTDIR/out8" "$TESTDIR/kr.alz" 2>&1); rc=$?
chk "$rc" 0 "T8: -utf8 extraction of EUC-KR-named member exits 0"
if [ -f "$TESTDIR/out8/$KR_NAME" ]; then
    ok "T8: filename restored as UTF-8 ($KR_NAME)"
else
    bad "T8: filename restored as UTF-8 (found: $(ls "$TESTDIR/out8"))"
fi
grepq "$KR_NAME" "$(ls "$TESTDIR/out8")" "T8: listed name is UTF-8 Korean"

# --- T9: corrupt-archive error text -------------------------------------------
echo "# T9 corrupt archive"
printf 'ALZ\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00' > "$TESTDIR/corrupt.alz"
OUT=$("$CC" -l "$TESTDIR/corrupt.alz" 2>&1); rc=$?
grepq "It's corrupted file." "$OUT" "T9: corrupt archive reports corruption"
chk "$rc" 0 "T9: upstream quirk — corrupt archive still exits 0"

# --- summary -------------------------------------------------------------------
echo "# total: PASS=$P FAIL=$F"
[ "$F" -eq 0 ]
