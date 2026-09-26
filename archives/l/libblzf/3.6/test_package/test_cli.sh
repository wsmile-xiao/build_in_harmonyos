#!/bin/sh
# test_package/test_cli.sh — CLI verification for the installed bin/lzf.
#
# Exercises the real packaged lzf(1) binary (never the build tree):
#   1. -h prints usage and exits 0 (non-empty guard: empty output never passes)
#   2. stdin/stdout pipe round-trip is byte-identical (non-empty .lzf guard)
#   3. file round-trip: f -> f.lzf (original unlinked) -> f restored byte-identical
#   4. negative: garbage input must fail decompression (proves the harness
#      detects real failures instead of passing empty comparisons)
#
# Env: LZF_BIN = absolute path of the packaged bin/lzf (preferred);
#      falls back to PATH lookup. TMPDIR/TMP/TEMP probed for writability
#      (OHOS /tmp is read-only); falls back to the script dir.
# Exit 0 only if all 4 checks pass (ctest Passed/Failed comes from this).
set -u

PASS=0
FAIL=0

# --- writable scratch (same policy as merged bwm/0.6.3 test.sh) ---
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SCRATCH_BASE="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ "$SCRATCH_BASE" = "/tmp" ] || [ "$SCRATCH_BASE" = "/tmp/" ]; then
    SCRATCH_BASE="$SCRIPT_DIR"
fi
if [ -n "$SCRATCH_BASE" ] && [ -d "$SCRATCH_BASE" ] 2>/dev/null; then
    if ! touch "$SCRATCH_BASE/.lzf_wtest_$$" 2>/dev/null; then
        SCRATCH_BASE="$SCRIPT_DIR"
    else
        rm -f "$SCRATCH_BASE/.lzf_wtest_$$"
    fi
else
    SCRATCH_BASE="$SCRIPT_DIR"
fi
SCRATCH="$(mktemp -d "${SCRATCH_BASE}/lzf-cli-test.XXXXXX" 2>/dev/null || echo "")"
if [ -z "$SCRATCH" ] || [ ! -d "$SCRATCH" ]; then
    SCRATCH="$SCRIPT_DIR/.scratch-$$"
    mkdir -p "$SCRATCH"
fi
trap 'rm -rf "$SCRATCH"' EXIT INT TERM

# --- locate the packaged binary (explicit path first, PATH fallback) ---
LZF="${LZF_BIN:-}"
if [ -z "$LZF" ] || [ ! -f "$LZF" ]; then
    if command -v lzf >/dev/null 2>&1; then
        LZF="$(command -v lzf)"
    else
        echo "[FAIL] packaged bin/lzf not found (LZF_BIN=${LZF_BIN:-(unset)}, not on PATH)"
        exit 1
    fi
fi
chmod +x "$LZF" 2>/dev/null || true  # HMDFS may ignore chmod; failure tolerated
echo "[test] using binary: $LZF"

# --- fixed input: 200 repetitions of a compressible sentence ---
INPUT="$SCRATCH/input.txt"
i=0
: > "$INPUT"
while [ "$i" -lt 200 ]; do
    echo "liblzf cli round-trip line $i: the quick brown fox jumps over the lazy dog 0123456789" >> "$INPUT"
    i=$((i + 1))
done
if [ ! -s "$INPUT" ]; then
    echo "[FAIL] cannot create test input"
    exit 1
fi

# --- 1. -h: usage on stdout/stderr, exit 0, non-empty ---
if out="$("$LZF" -h 2>&1)"; then
    if [ -n "$out" ] && echo "$out" | grep -qi "usage"; then
        echo "[PASS] lzf -h prints usage"
        PASS=$((PASS + 1))
    else
        echo "[FAIL] lzf -h output unexpected: $(echo "$out" | head -c 200)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "[FAIL] lzf -h exit non-zero"
    FAIL=$((FAIL + 1))
fi

# --- 2. pipe round-trip: stdin -> stdout must be byte-identical ---
if "$LZF" < "$INPUT" > "$SCRATCH/pipe.lzf" 2>"$SCRATCH/pipe_compress.err"; then
    if [ -s "$SCRATCH/pipe.lzf" ]; then
        if "$LZF" -d < "$SCRATCH/pipe.lzf" > "$SCRATCH/pipe.out" 2>"$SCRATCH/pipe_decompress.err"; then
            if cmp -s "$INPUT" "$SCRATCH/pipe.out"; then
                echo "[PASS] pipe round-trip byte-identical (compressed $(wc -c < "$SCRATCH/pipe.lzf") bytes)"
                PASS=$((PASS + 1))
            else
                echo "[FAIL] pipe round-trip differs from input"
                FAIL=$((FAIL + 1))
            fi
        else
            echo "[FAIL] pipe decompress exit non-zero: $(head -c 200 "$SCRATCH/pipe_decompress.err")"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "[FAIL] pipe compress produced empty output (empty-vs-empty guard)"
        FAIL=$((FAIL + 1))
    fi
else
    echo "[FAIL] pipe compress exit non-zero: $(head -c 200 "$SCRATCH/pipe_compress.err")"
    FAIL=$((FAIL + 1))
fi

# --- 3. file round-trip: f -> f.lzf -> f, byte-identical ---
cp "$INPUT" "$SCRATCH/f1"
if "$LZF" "$SCRATCH/f1" 2>"$SCRATCH/file_compress.err"; then
    if [ -s "$SCRATCH/f1.lzf" ] && [ ! -e "$SCRATCH/f1" ]; then
        if "$LZF" -d "$SCRATCH/f1.lzf" 2>"$SCRATCH/file_decompress.err"; then
            if [ -f "$SCRATCH/f1" ] && cmp -s "$INPUT" "$SCRATCH/f1"; then
                echo "[PASS] file round-trip byte-identical"
                PASS=$((PASS + 1))
            else
                echo "[FAIL] file round-trip differs from input"
                FAIL=$((FAIL + 1))
            fi
        else
            echo "[FAIL] file decompress exit non-zero: $(head -c 200 "$SCRATCH/file_decompress.err")"
            FAIL=$((FAIL + 1))
        fi
    else
        echo "[FAIL] file compress did not produce f1.lzf / unlink f1"
        FAIL=$((FAIL + 1))
    fi
else
    echo "[FAIL] file compress exit non-zero: $(head -c 200 "$SCRATCH/file_compress.err")"
    FAIL=$((FAIL + 1))
fi

# --- 4. negative: garbage must fail decompression ---
printf 'this is definitely not an lzf stream !!!!' > "$SCRATCH/garbage.lzf"
if "$LZF" -d < "$SCRATCH/garbage.lzf" > "$SCRATCH/garbage.out" 2>/dev/null; then
    echo "[FAIL] garbage decompress unexpectedly succeeded (harness must catch failures)"
    FAIL=$((FAIL + 1))
else
    echo "[PASS] garbage decompress fails as expected"
    PASS=$((PASS + 1))
fi

echo "=== cli summary: ${PASS}/4 passed, ${FAIL} failed ==="
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne 4 ]; then
    exit 1
fi
exit 0
