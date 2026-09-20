#!/bin/sh
# Functional smoke test for the packaged minibwa executable.
# Mirrors test_package/conanfile.py: version, index+map round trip, SAM checks.
# POSIX sh only: no pipefail, no seq (both unavailable in OHOS /bin/sh).
set -eu

WORK="$PWD/minibwa-test-work"
rm -rf "$WORK"
mkdir -p "$WORK"

# EXIT trap: capture the original status first and re-exit with it
# explicitly — commands inside the trap (rm/find) must never mask the
# real failure exit code.
cleanup() {
    status=$?
    if [ "$status" -eq 0 ]; then
        rm -rf "$WORK" || true
    else
        echo "minibwa functional test failed (exit $status); preserving logs in $WORK" >&2
        find "$WORK" -maxdepth 1 -type f -print >&2 || true
    fi
    exit "$status"
}
trap cleanup EXIT

BIN="${MINIBWA_BIN:-minibwa}"

echo "[test] minibwa --help"
"$BIN" --help > "$WORK/help.txt" 2>&1
grep -q "Usage: minibwa" "$WORK/help.txt"

echo "[test] minibwa version"
"$BIN" version > "$WORK/version.txt" 2>&1
grep -q "0.4" "$WORK/version.txt"

# Tiny generated reference (168 bp) with a 100 bp exact-substring read,
# the same deterministic dataset proven on this target in test_package.
cat > "$WORK/tiny-ref.fa" <<'EOF'
>tiny
ACGTGCAATGTCAGTCAAGTCAGTTGACGATCGATCGTACGTAGCTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCGATCGTACGATCGATCGTACGATCGTACGATCGTACGATCGTACGATCGTAGCTAACGATCGATCGTACGATCGTACGATCGATCGTACGTAGCTAACGATCG
EOF
READ=$(sed -n '2p' "$WORK/tiny-ref.fa" | cut -c 21-120)
QUAL=$(awk 'BEGIN { for (i = 0; i < 100; i++) printf "F" }')
printf '@r1\n%s\n+\n%s\n' "$READ" "$QUAL" > "$WORK/tiny-read.fq"

echo "[test] minibwa index"
"$BIN" index "$WORK/tiny-ref.fa" > "$WORK/index.log" 2>&1

echo "[test] minibwa map"
"$BIN" map "$WORK/tiny-ref.fa" "$WORK/tiny-read.fq" > "$WORK/map.sam" 2> "$WORK/map.err"

awk 'BEGIN { ok = 0 }
     !/^@/ && $3 == "tiny" && $4 == 21 && $6 == "100M" { ok = 1 }
     END { exit ok ? 0 : 1 }' "$WORK/map.sam"

echo "minibwa functional test: PASS"
