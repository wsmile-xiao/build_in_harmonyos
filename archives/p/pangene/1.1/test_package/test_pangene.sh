#!/usr/bin/env bash
# test_pangene.sh — functional test for the pangene pangenome gene graph tool.
# Runs in conanrun env (PATH includes the installed package bin/).
#
# Fixture: official upstream quick-start data test/C4/*.paf (33 miniprot
# PAF alignments across 8 primate assemblies), decompressed to plain text
# (zlib gzopen transparently reads uncompressed files).
#
# Assertions:
#   1. --version prints "1.1-r231" (pangene.h PG_VERSION) and exits 0.
#   2. README quick-start (pangene test/C4/*.paf > out.gfa) exits 0.
#   3. Output GFA contains at least one S (segment) line.
#   4. Output GFA contains at least one L (edge) line.
#   5. Output GFA contains at least one W (walk) line.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TESTDATA="$SCRIPT_DIR/testdata"
WORK="$(pwd)/pangene-testdata"
rm -rf "$WORK" && mkdir -p "$WORK"

# --------------------------------------------------------------------------
# Test 1: version — `pangene --version` prints "1.1-r231" and exits 0.
# --------------------------------------------------------------------------
if version_out="$(pangene --version 2>&1)" && echo "$version_out" | grep -q "1.1-r231"; then
    echo "PASS [1/5]: pangene version is 1.1-r231"
else
    echo "FAIL [1/5]: unexpected version output: $version_out"
    exit 1
fi

# --------------------------------------------------------------------------
# Test 2: upstream README quick-start on official C4 fixtures, exit 0.
# --------------------------------------------------------------------------
if pangene "$TESTDATA"/C4/*.paf > "$WORK/out.gfa" 2> "$WORK/run.log"; then
    echo "PASS [2/5]: quick-start run exits 0"
else
    echo "FAIL [2/5]: pangene exited non-zero"
    cat "$WORK/run.log"
    exit 1
fi

# --------------------------------------------------------------------------
# Tests 3-5: GFA structure — S/L/W lines present.
# --------------------------------------------------------------------------
if [ -s "$WORK/out.gfa" ] && grep -c '^S' "$WORK/out.gfa" | grep -q '[1-9]'; then
    echo "PASS [3/5]: GFA output has S (segment) lines"
else
    echo "FAIL [3/5]: no S lines in output"
    head -5 "$WORK/out.gfa"
    exit 1
fi

if grep -q '^L' "$WORK/out.gfa"; then
    echo "PASS [4/5]: GFA output has L (edge) lines"
else
    echo "FAIL [4/5]: no L lines in output"
    exit 1
fi

if grep -q '^W' "$WORK/out.gfa"; then
    echo "PASS [5/5]: GFA output has W (walk) lines"
else
    echo "FAIL [5/5]: no W lines in output"
    exit 1
fi

echo "GFA stats: $(grep -c '^S' "$WORK/out.gfa") S / $(grep -c '^L' "$WORK/out.gfa") L / $(grep -c '^W' "$WORK/out.gfa") W"
rm -rf "$WORK"
echo "ALL TESTS PASSED (5/5)"
exit 0
