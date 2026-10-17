#!/bin/sh
# test_package/test.sh — mp3cat real CLI behavior test.
# Invoked by conanfile.py:  sh test.sh <three.mp3> <dirty.mp3> <tmpdir>
# mp3cat is on PATH via the conanrun environment.
set -eu

THREE_MP3="$1"
DIRTY_MP3="$2"
TMPDIR_OUT="$3"

# ── 1. --version → exit 0 ─────────────────────────────────────────────
mp3cat --version

# ── 2. --help → exit 0 ─────────────────────────────────────────────────
mp3cat --help >/dev/null 2>&1

# ── 3. Passthrough: 3 valid frames → 2 frames emitted (lookahead) ───────
#   exit 0, output = 192 bytes (96-byte frame × 2, trailing frame dropped)
mp3cat - - < "$THREE_MP3" > "$TMPDIR_OUT/out_passthrough.mp3"
actual=$(wc -c < "$TMPDIR_OUT/out_passthrough.mp3")
[ "$actual" -eq 192 ] || {
    echo "FAIL: passthrough output size: expected 192, got $actual" >&2
    exit 1
}

# ── 4. Cleaning: garbage + 3 frames → 2 frames (garbage stripped) ──────
#   exit 0, output byte-for-byte identical to passthrough (192 bytes)
mp3cat - - < "$DIRTY_MP3" > "$TMPDIR_OUT/out_clean.mp3"
cmp -s "$TMPDIR_OUT/out_passthrough.mp3" "$TMPDIR_OUT/out_clean.mp3" || {
    echo "FAIL: cleaned output differs from valid passthrough output" >&2
    exit 1
}

# ── 5. Empty input → exit 0, 0 bytes output ────────────────────────────
mp3cat - - < /dev/null > "$TMPDIR_OUT/out_empty.mp3"
actual=$(wc -c < "$TMPDIR_OUT/out_empty.mp3")
[ "$actual" -eq 0 ] || {
    echo "FAIL: empty input produced $actual bytes, expected 0" >&2
    exit 1
}

# ── 6. Bad usage (1 positional arg, need 2) → exit 1 ───────────────────
if mp3cat only_one_arg 2>/dev/null; then
    echo "FAIL: expected exit 1 for bad usage (1 arg), got exit 0" >&2
    exit 1
fi

echo "mp3cat test_package: ALL CHECKS PASSED (6 checks)"
