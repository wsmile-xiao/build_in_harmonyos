#!/bin/bash
# test_lxsplit.sh — lxsplit 0.2.4 functional round-trip test
# Usage: bash test_lxsplit.sh /abs/path/to/lxsplit
#
# Creates a small file, splits it, joins the pieces back, and verifies the
# recovered file is byte-for-byte identical to the original.

set -euo pipefail

LXSPLIT="${1:?usage: test_lxsplit.sh /path/to/lxsplit}"

echo "=== lxsplit functional test ==="
echo "    binary: $LXSPLIT"

# Sanity: the packaged binary must exist and be executable.
if [ ! -x "$LXSPLIT" ]; then
    echo "        [fail] packaged lxsplit not found or not executable: $LXSPLIT"
    exit 1
fi
echo "        [ok] packaged binary present"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT

# --- 1. create a small file with deterministic, identifiable content ---
# ~50 lines * ~77 bytes ~ 3850 bytes; a 1 KB split yields 4 pieces.
{
    for i in $(seq 1 50); do
        echo "line ${i}: lxsplit functional test payload ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    done
} > "$WORK/input.bin"
echo "        [ok] created input.bin ($(wc -c < "$WORK/input.bin") bytes)"

# --- 2. split with the packaged lxsplit (1 KB pieces) ---
cd "$WORK"
"$LXSPLIT" -s input.bin 1k
# Expected pieces: input.bin.001 input.bin.002 input.bin.003 input.bin.004
piece_count=$(ls input.bin.0* 2>/dev/null | wc -l)
if [ "$piece_count" -ne 4 ]; then
    echo "        [fail] split produced ${piece_count} piece(s), expected exactly 4"
    exit 1
fi
echo "        [ok] split produced ${piece_count} pieces"

# --- 3. save a reference, remove the original, then join the pieces back ---
# lxsplit join writes the merged file to <basename> (input.bin) but ABORTS
# ("input.bin already exists! Aborting...") if that file already exists, so
# the original must be removed before joining. Keep a reference copy first.
cp input.bin reference.bin
rm -f input.bin
"$LXSPLIT" -j input.bin.001
if [ ! -f input.bin ]; then
    echo "        [fail] join did not reproduce input.bin"
    exit 1
fi
echo "        [ok] join reproduced input.bin ($(wc -c < input.bin) bytes)"

# --- 4. verify byte-for-byte identity ---
if cmp -s reference.bin input.bin; then
    echo "        [ok] recovered file is byte-for-byte identical to original"
else
    echo "        [fail] recovered file differs from original"
    cmp reference.bin input.bin || true
    exit 1
fi

# --- 5. verify checksums as a second independent check ---
ref_sum=$(sha256sum reference.bin | awk '{print $1}')
got_sum=$(sha256sum input.bin | awk '{print $1}')
if [ "$ref_sum" = "$got_sum" ]; then
    echo "        [ok] sha256 matches: $got_sum"
else
    echo "        [fail] sha256 mismatch: ref=$ref_sum got=$got_sum"
    exit 1
fi

echo "=== All tests passed ==="
