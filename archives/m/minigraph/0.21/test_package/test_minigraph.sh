#!/usr/bin/env bash
# test_minigraph.sh — functional test for the minigraph sequence-to-graph mapper.
# Runs in conanrun env (PATH includes the installed package bin/).
#
# Fixture (deterministic, programmatically generated, text-only; fixed-seed
# LCG random sequence — no external data):
#   testdata/ref.fa    ref1: 16000bp reference
#   testdata/sample.fa sam1: 15000bp sample = ref[:4000] + ref[5000:]
#                       (a 1000bp deletion vs the reference at offset 4000)
#
# 18 assertions — 14 functional: version, graph build bubbles, ACGT
# segments, determinism, L-line CIGARs, linear PAF fields, GAF ds:Z tag,
# handwritten GFA input, --call BED output, gzip input, missing-graph input,
# missing-sample input, no-args; plus 4 HarmonyOS-specific: ELF identity,
# no RPATH, no host paths, deployed-mode run.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTDATA="$SCRIPT_DIR/testdata"
WORK="$(pwd)/minigraph-testdata"
rm -rf "$WORK" && mkdir -p "$WORK"

# --------------------------------------------------------------------------
# Test 1: version — `minigraph --version` prints "0.21-r606" and exits 0.
# --------------------------------------------------------------------------
if version_out="$(minigraph --version 2>&1)" && echo "$version_out" | grep -q "0.21-r606"; then
    echo "PASS [1/18]: minigraph version is 0.21-r606"
else
    echo "FAIL [1/18]: unexpected version output: $version_out"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 2: graph construction — -cxggs -c with lowered thresholds builds a
# graph that absorbs the 1000bp deletion as a bubble (S >= 2 segments and
# L >= 1 edges), not a single linear chain.
# --------------------------------------------------------------------------
minigraph -cxggs -c -l1k -d1k "$TESTDATA/ref.fa" "$TESTDATA/sample.fa" \
    > "$WORK/graph.gfa" 2>"$WORK/build.log"
s_count=$(grep -c '^S' "$WORK/graph.gfa" || true)
l_count=$(grep -c '^L' "$WORK/graph.gfa" || true)
if [ "$s_count" -ge 2 ] && [ "$l_count" -ge 1 ]; then
    echo "PASS [2/18]: graph has structural variation bubbles (S=$s_count, L=$l_count)"
else
    echo "FAIL [2/18]: expected S>=2/L>=1 bubble graph, got S=$s_count L=$l_count"
    cat "$WORK/graph.gfa"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 3: structural output validity — every S segment sequence is pure ACGT.
# --------------------------------------------------------------------------
if awk -F'\t' '/^S/ {
    n = length($3); ok = 1
    for (i = 1; i <= n; i++) {
        c = substr($3, i, 1)
        if (c != "A" && c != "C" && c != "G" && c != "T") { ok = 0; break }
    }
    if (!ok) { print "bad segment: " $2; exit 1 }
}' "$WORK/graph.gfa"; then
    echo "PASS [3/18]: all graph segments are pure ACGT sequences"
else
    echo "FAIL [3/18]: graph contains a non-ACGT segment sequence"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 4: determinism — the same graph build run twice is byte-identical.
# --------------------------------------------------------------------------
minigraph -cxggs -c -l1k -d1k "$TESTDATA/ref.fa" "$TESTDATA/sample.fa" \
    > "$WORK/graph2.gfa" 2>/dev/null
if cmp -s "$WORK/graph.gfa" "$WORK/graph2.gfa"; then
    echo "PASS [4/18]: graph construction is deterministic (byte-identical)"
else
    echo "FAIL [4/18]: graph construction differs between runs"
    diff "$WORK/graph.gfa" "$WORK/graph2.gfa" | head -5
    exit 1
fi

# --------------------------------------------------------------------------
# Test 5: GFA L lines have a valid CIGAR field (0M-style match or *).
# --------------------------------------------------------------------------
l_bad=$(grep '^L' "$WORK/graph.gfa" | awk -F'\t' '$6 !~ /^[0-9]+M$/ && $6 != "*"' | wc -l || true)
if [ "$l_bad" -eq 0 ]; then
    echo "PASS [5/18]: GFA L-line CIGARs are valid"
else
    echo "FAIL [5/18]: invalid L-line CIGAR found"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 6: linear mapping — default preset maps sample to FASTA reference.
# Expect exactly 1 PAF line: sam1 -> ref1.
# --------------------------------------------------------------------------
minigraph "$TESTDATA/ref.fa" "$TESTDATA/sample.fa" > "$WORK/map.paf" 2>"$WORK/map.log"
paf_lines=$(grep -vc '^$' "$WORK/map.paf" || true)
if [ "$paf_lines" -eq 1 ]; then
    echo "PASS [6/18]: PAF mapping has exactly 1 hit"
else
    echo "FAIL [6/18]: expected 1 PAF hit, got $paf_lines"
    cat "$WORK/map.paf"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 7: PAF fields — sam1 -> ref1, strand +, target length 16000,
# query block within [1,15000], target block within [1,16000]
# (target block 15992 > query 15000 is expected: it spans the deletion),
# target interval ordered and inside [0,16000].
# --------------------------------------------------------------------------
awk -F'\t' '
    NR == 1 {
        if ($1 != "sam1" || $6 != "ref1") { print "FAIL [7/18]: wrong query/target: " $1 " -> " $6; exit 1 }
        if ($5 != "+")                    { print "FAIL [7/18]: wrong strand: " $5; exit 1 }
        if ($7 != 16000)                  { print "FAIL [7/18]: wrong target length: " $7; exit 1 }
        if ($10 < 1 || $10 > 15000)       { print "FAIL [7/18]: bad query block length: " $10; exit 1 }
        if ($11 < 1 || $11 > 16000)       { print "FAIL [7/18]: bad target block length: " $11; exit 1 }
        if ($8 >= $9 || $8 < 0 || $9 > 16000) { print "FAIL [7/18]: bad target interval: " $8 "-" $9; exit 1 }
        print "PASS [7/18]: PAF fields consistent (sam1->ref1, +, tlen=16000, qblk=" $10 ", tblk=" $11 ")"
        exit 0
    }
' "$WORK/map.paf" || exit 1

# --------------------------------------------------------------------------
# Test 8: graph mapping — -cxlr preset maps sample to the built graph.
# GAF output carries the graph-specific ds:Z tag (path coordinates) that
# linear PAF output never emits; target column names the graph path (ref1).
# --------------------------------------------------------------------------
minigraph -cxlr "$WORK/graph.gfa" "$TESTDATA/sample.fa" \
    > "$WORK/map.gaf" 2>"$WORK/gaf.log"
gaf_lines=$(grep -vc '^$' "$WORK/map.gaf" || true)
if [ "$gaf_lines" -ge 1 ] && grep -q 'ds:Z:' "$WORK/map.gaf" \
    && awk -F'\t' 'NR==1 && $6 ~ /^ref1/{found=1} END{exit !found}' "$WORK/map.gaf"; then
    echo "PASS [8/18]: GAF graph mapping emits path output with ds:Z tag ($gaf_lines lines)"
else
    echo "FAIL [8/18]: GAF output missing ds:Z path hit (lines=$gaf_lines)"
    cat "$WORK/map.gaf"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 9: handwritten GFA input — a minimal graph written by hand (H + single
# S line with SN:Z/SO tags, no L lines), not produced by minigraph, is
# accepted as mapping target.  The sample's 1000bp deletion must be reported
# exactly: NM:i:1000 on the single GAF row (path coordinates via SN:Z).
# --------------------------------------------------------------------------
python3 - "$TESTDATA/ref.fa" "$WORK/handwritten.gfa" <<'PYEOF'
import sys
seq = []
with open(sys.argv[1]) as f:
    for line in f:
        if not line.startswith(">"):
            seq.append(line.strip())
seq = "".join(seq)
assert len(seq) == 16000, "fixture ref1 length changed: %d" % len(seq)
with open(sys.argv[2], "w") as f:
    f.write("H\tVN:Z:1.0\n")
    f.write("S\tref1\t%s\tSN:Z:ref1\tSO:i:0\n" % seq)
PYEOF
minigraph -cxlr "$WORK/handwritten.gfa" "$TESTDATA/sample.fa" \
    > "$WORK/hw.gaf" 2>"$WORK/hw.log"
hw_rows=$(grep -vc '^$' "$WORK/hw.gaf" || true)
if [ "$hw_rows" -eq 1 ] && grep -q "NM:i:1000" "$WORK/hw.gaf" \
    && awk -F'\t' 'NR==1 && $6 ~ /^>?ref1/{found=1} END{exit !found}' "$WORK/hw.gaf"; then
    echo "PASS [9/18]: handwritten GFA accepted; deletion reported exactly (NM:i:1000)"
else
    echo "FAIL [9/18]: handwritten GFA mapping wrong (rows=$hw_rows)"
    cat "$WORK/hw.gaf"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 10: --call variant calling — -xasm --call on the graph outputs BED
# lines; the deletion injected at reference offset 4000..5000 is detected.
# --------------------------------------------------------------------------
minigraph -xasm -l1k -d1k --call "$WORK/graph.gfa" "$TESTDATA/sample.fa" \
    > "$WORK/call.bed" 2>"$WORK/call.log"
bed_lines=$(grep -vc '^$' "$WORK/call.bed" || true)
if [ "$bed_lines" -ge 1 ] && awk -F'\t' '
    NR == 1 && $1 == "ref1" && $2 < 4500 && $3 > 4500 {
        print "PASS [10/18]: --call detects the injected deletion (ref1:" $2 "-" $3 ")"
        exit 0
    }
    { print "FAIL [10/18]: unexpected BED first row: " $0; exit 1 }
' "$WORK/call.bed"; then :; else
    echo "FAIL [10/18]: --call output wrong (lines=$bed_lines)"
    cat "$WORK/call.bed"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 11: gzip input — a gzipped reference still maps (zlib link check).
# --------------------------------------------------------------------------
gzip -c "$TESTDATA/ref.fa" > "$WORK/ref.fa.gz"
minigraph "$WORK/ref.fa.gz" "$TESTDATA/sample.fa" > "$WORK/gz.paf" 2>/dev/null
gz_lines=$(grep -vc '^$' "$WORK/gz.paf" || true)
if [ "$gz_lines" -eq 1 ] && awk -F'\t' 'NR==1 && $6=="ref1"{found=1} END{exit !found}' "$WORK/gz.paf"; then
    echo "PASS [11/18]: gzip reference input maps to ref1 (zlib works)"
else
    echo "FAIL [11/18]: gzip input mapping failed (lines=$gz_lines)"
    cat "$WORK/gz.paf"
    exit 1
fi

# --------------------------------------------------------------------------
# Tests 12-13: negative input — missing inputs must fail with rc!=0 and a
# real error on stderr ("[ERROR] failed to load the graph" for a missing
# first input; "ERROR: failed to open file" for a missing second input).
# --------------------------------------------------------------------------
miss_rc=0
minigraph "$TESTDATA/does-not-exist.fa" "$TESTDATA/sample.fa" \
    > "$WORK/miss.paf" 2>"$WORK/miss.log" || miss_rc=$?
if [ "$miss_rc" -ne 0 ] && grep -qiE "(failed to load the graph|failed to open)" "$WORK/miss.log"; then
    echo "PASS [12/18]: missing graph input rejected with rc=$miss_rc and error message"
else
    echo "FAIL [12/18]: missing-file behavior wrong (rc=$miss_rc)"
    cat "$WORK/miss.log"
    exit 1
fi
miss2_rc=0
minigraph "$TESTDATA/ref.fa" "$TESTDATA/does-not-exist.fa" \
    > "$WORK/miss2.paf" 2>"$WORK/miss2.log" || miss2_rc=$?
if [ "$miss2_rc" -ne 0 ] && grep -qiE "failed to open" "$WORK/miss2.log"; then
    echo "PASS [13/18]: missing sample input rejected with rc=$miss2_rc and error message"
else
    echo "FAIL [13/18]: missing sample input behavior wrong (rc=$miss2_rc)"
    cat "$WORK/miss2.log"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 14: negative input — no arguments prints Usage to stderr with rc=1
# (documented upstream behavior; assert rc != 0 and non-empty stderr).
# --------------------------------------------------------------------------
noargs_rc=0
minigraph > "$WORK/noargs.out" 2>"$WORK/noargs.log" || noargs_rc=$?
noargs_err=$(grep -vc '^$' "$WORK/noargs.log" || true)
if [ "$noargs_rc" -ne 0 ] && [ "$noargs_err" -ge 1 ]; then
    echo "PASS [14/18]: no-args invocation fails with rc=$noargs_rc and Usage on stderr"
else
    echo "FAIL [14/18]: no-args behavior wrong (rc=$noargs_rc, stderr lines=$noargs_err)"
    exit 1
fi

rm -rf "$WORK"
echo "ALL FUNCTIONAL TESTS PASSED (14/14)"

# ==========================================================================
# HarmonyOS-specific checks (only on OHOS targets; skipped elsewhere with a
# visible SKIP marker).  These verify the binary is a genuine OHOS aarch64
# executable: ELF64/AArch64, musl PT_INTERP, presence of the .codesign
# section (required by the OHOS code-signing toolchain), and absence of
# RPATH/RUNPATH or host build paths that would break on-device deployment.
# ==========================================================================

if [ "$(uname -m)" != "aarch64" ] || [ ! -e /lib/ld-musl-aarch64.so.1 ]; then
    echo "SKIP [15-18/18]: HarmonyOS-specific checks (not on an OHOS aarch64 host)"
    echo "ALL TESTS DONE (14 functional passed, 4 harmony skipped)"
    exit 0
fi

# Locate the installed minigraph via PATH (conanrun env).
MG_BIN="$(command -v minigraph)"
if [ -z "$MG_BIN" ]; then
    echo "FAIL: minigraph not found in PATH"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 15: ELF identity — 64-bit little-endian AArch64 ELF, PIE (ET_DYN),
# musl PT_INTERP, .codesign section present.
# --------------------------------------------------------------------------
python3 - "$MG_BIN" <<'PYEOF'
import struct, sys

path = sys.argv[1]
with open(path, "rb") as f:
    data = f.read()

# ELF identification
assert data[:4] == b"\x7fELF", "not an ELF file"
ei_class, ei_data = data[4], data[5]
assert ei_class == 2, "not ELF64 (EI_CLASS=%d)" % ei_class
assert ei_data == 1, "not little-endian (EI_DATA=%d)" % ei_data

# ELF header
e_type, e_machine = struct.unpack_from("<HH", data, 16)
assert e_machine == 0xB7, "not AArch64 (e_machine=0x%x)" % e_machine
assert e_type == 3, "not PIE/ET_DYN (e_type=%d)" % e_type

# Program headers: find PT_INTERP (type 3)
e_phoff, = struct.unpack_from("<Q", data, 32)
e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
interp = None
for i in range(e_phnum):
    off = e_phoff + i * e_phentsize
    p_type, = struct.unpack_from("<I", data, off)
    if p_type == 3:  # PT_INTERP
        p_offset, p_filesz = struct.unpack_from("<QQ", data, off + 8)
        interp = data[p_offset:p_offset + p_filesz].split(b"\0")[0].decode()
        break
assert interp == "/lib/ld-musl-aarch64.so.1", \
    "unexpected PT_INTERP: %r" % interp

# Section headers: .codesign must exist
e_shoff, = struct.unpack_from("<Q", data, 40)
e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", data, 58)
shstr_off, shstr_size = struct.unpack_from("<QQ", data,
    e_shoff + e_shstrndx * e_shentsize + 24)
shstrtab = data[shstr_off:shstr_off + shstr_size]
sections = set()
for i in range(e_shnum):
    off = e_shoff + i * e_shentsize
    name_off, = struct.unpack_from("<I", data, off)
    end = shstrtab.find(b"\0", name_off)
    sections.add(shstrtab[name_off:end].decode())
assert ".codesign" in sections, "missing .codesign section: %s" % sorted(
    s for s in sections if s)

print("PASS [15/18]: ELF64 little-endian AArch64 PIE with musl INTERP "
      "and .codesign section")
PYEOF

# --------------------------------------------------------------------------
# Test 16: no RPATH/RUNPATH — dynamic section must not contain DT_RPATH (15)
# or DT_RUNPATH (29); NEEDED must be system libs only (libz, libc).
# --------------------------------------------------------------------------
python3 - "$MG_BIN" <<'PYEOF'
import struct, sys

path = sys.argv[1]
with open(path, "rb") as f:
    data = f.read()

e_phoff, = struct.unpack_from("<Q", data, 32)
e_phentsize, e_phnum = struct.unpack_from("<HH", data, 54)
dyn = None
for i in range(e_phnum):
    off = e_phoff + i * e_phentsize
    p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz = \
        struct.unpack_from("<IIQQQQ", data, off)
    if p_type == 2:  # PT_DYNAMIC
        dyn = (p_offset, p_filesz)
        break
assert dyn, "no PT_DYNAMIC segment"

dt_strtab = None
rpath_tags = []
needed = []
off, size = dyn
for i in range(size // 16):
    tag, val = struct.unpack_from("<QQ", data, off + i * 16)
    if tag == 0:
        break
    if tag == 5:   # DT_STRTAB
        dt_strtab = val
    elif tag in (15, 29):  # DT_RPATH / DT_RUNPATH
        rpath_tags.append(tag)
    elif tag == 1:  # DT_NEEDED
        needed.append(val)
assert not rpath_tags, "found DT_RPATH/DT_RUNPATH tags: %r" % rpath_tags
assert dt_strtab is not None, "no DT_STRTAB in dynamic section"

# NEEDED entries hold offsets into DT_STRTAB.  Resolve the strtab file
# offset via program headers, then read names.
def vaddr_to_off(v):
    for i in range(e_phnum):
        o = e_phoff + i * e_phentsize
        p_type, p_flags, p_offset, p_vaddr, p_paddr, p_filesz = \
            struct.unpack_from("<IIQQQQ", data, o)
        if p_type == 1 and p_vaddr <= v < p_vaddr + p_filesz:
            return p_offset + (v - p_vaddr)
    return None

strtab_off = vaddr_to_off(dt_strtab)
assert strtab_off is not None, "DT_STRTAB vaddr not mapped by any segment"
allowed = {"libz.so", "libc.so", "libm.so", "libpthread.so"}
names = set()
for n in needed:
    end = data.find(b"\0", strtab_off + n)
    name = data[strtab_off + n:end].decode()
    assert name in allowed, "unexpected DT_NEEDED entry: %r" % name
    names.add(name)
print("PASS [16/18]: no DT_RPATH/DT_RUNPATH; NEEDED limited to %s" %
      sorted(names))
PYEOF

# --------------------------------------------------------------------------
# Test 17: no host build paths embedded in the binary (no /storage/, /home/,
# /Users/, /data/service — the toolchain prefix-map must have scrubbed
# DWARF comp_dir and sysroot references).
# --------------------------------------------------------------------------
if python3 - "$MG_BIN" <<'PYEOF'
import sys
with open(sys.argv[1], "rb") as f:
    data = f.read()
for pat in (b"/storage/", b"/home/", b"/Users/", b"/data/service"):
    if pat in data:
        # Report the offending context for debugging.
        i = data.find(pat)
        ctx = data[max(0, i - 40):i + 60]
        print("FAIL [17/18]: host path %r found: ...%r..." % (pat, ctx),
              file=sys.stderr)
        sys.exit(1)
sys.exit(0)
PYEOF
then
    echo "PASS [17/18]: no host build paths embedded in the binary"
else
    echo "FAIL [17/18]: host path leak detected"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 18: real command execution on the OHOS host — build a tiny graph and
# verify the deployed binary produces the deterministic bubble structure
# (fresh run in a clean work dir).
# --------------------------------------------------------------------------
mkdir -p "$WORK"
"$MG_BIN" -cxggs -c -l1k -d1k "$TESTDATA/ref.fa" "$TESTDATA/sample.fa" \
    > "$WORK/final.gfa" 2>/dev/null
s=$(grep -c '^S' "$WORK/final.gfa" || true)
l=$(grep -c '^L' "$WORK/final.gfa" || true)
if [ "$s" -ge 2 ] && [ "$l" -ge 1 ]; then
    echo "PASS [18/18]: deployed-mode graph build produces bubble graph (S=$s, L=$l)"
else
    echo "FAIL [18/18]: deployed-mode graph build failed (S=$s L=$l)"
    exit 1
fi

rm -rf "$WORK"
echo "ALL TESTS PASSED (18/18)"
exit 0
