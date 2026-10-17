#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer tests for the ndiff executable.
set -euo pipefail

WORKDIR="${TMPDIR:-.}/ndiff-test-package-$$"
mkdir -p "$WORKDIR"
trap 'rm -rf "$WORKDIR"' EXIT

echo "[test] ndiff --version"
ndiff --version 2>&1 | grep -q "Version 2.00"
echo "OK: --version reports upstream 2.00"

cat > "$WORKDIR/a.txt" <<'EOF'
sample 1.000000
EOF

cat > "$WORKDIR/b.txt" <<'EOF'
sample 1.000001
EOF

echo "[test] ndiff accepts values within relative tolerance"
ndiff --relative-error 1e-3 --quiet "$WORKDIR/a.txt" "$WORKDIR/b.txt"
echo "OK: tolerance comparison succeeded"

echo "[test] ndiff reports values outside relative tolerance"
set +e
ndiff --relative-error 1e-9 "$WORKDIR/a.txt" "$WORKDIR/b.txt" > "$WORKDIR/diff.out" 2>&1
rc=$?
set -e
if [ "$rc" -eq 0 ]; then
    echo "FAIL: expected ndiff to report an out-of-tolerance difference"
    exit 1
fi
grep -q "relative error" "$WORKDIR/diff.out"
grep -q "1.000001" "$WORKDIR/diff.out"
echo "OK: out-of-tolerance difference reported"
