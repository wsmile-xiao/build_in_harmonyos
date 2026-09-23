#!/bin/sh
# mpsolve consumer smoke test (R34: runs the packaged binary, asserts behavior).
# Feeds x^2 - 2 (roots +/-1.4142135623...) in the documented MPSolve input
# format and checks both roots appear in the output.
BIN="$1"
TMP=$(mktemp -d) || exit 1
trap 'rm -rf "$TMP"' EXIT

cat > "$TMP/poly.txt" <<'EOF'
! x^2 - 2
Degree=2;
Monomial;
Real;
Integer;
-2
0
1
EOF

"$BIN" "$TMP/poly.txt" > "$TMP/out.txt" 2>"$TMP/err.txt"
rc=$?
if [ $rc -ne 0 ]; then
    echo "mpsolve exited $rc" >&2
    head -5 "$TMP/err.txt" >&2
    exit 1
fi

# MPSolve prints roots in scientific notation, e.g. "(-0.14142135623731e1, 0.e-19)"
if ! grep -qE '\(0\.1414213[0-9]*e1' "$TMP/out.txt"; then
    echo "positive root sqrt(2) not found in output" >&2
    head -10 "$TMP/out.txt" >&2
    exit 1
fi
if ! grep -qE '\(-0\.1414213[0-9]*e1' "$TMP/out.txt"; then
    echo "negative root -sqrt(2) not found in output" >&2
    head -10 "$TMP/out.txt" >&2
    exit 1
fi
echo "mpsolve smoke ok: roots +/-1.41421356 found for x^2 - 2"
