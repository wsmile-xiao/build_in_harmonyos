#!/bin/sh
# Consumer test for complexity: verify the packaged binary executes and
# really scores C source (not a stub that exits 0).
# Usage: test_complexity.sh <path-to-complexity>
set -u

BIN="${1:?usage: test_complexity.sh <path-to-complexity>}"

passed=0
failed=0

# Case 1: complexity --version prints the 1.13 version banner and exits 0
ver=$("$BIN" --version 2>&1)
rc=$?
if [ $rc -eq 0 ] && printf '%s' "$ver" | grep -q "1\.13"; then
    echo "PASS: complexity --version -> $(printf '%s' "$ver" | head -n 1)"
    passed=$((passed + 1))
else
    echo "FAIL: complexity --version rc=$rc output=$ver"
    failed=$((failed + 1))
fi

# Case 2: complexity scores a sample C file and prints a non-empty
# "Complexity Scores" table naming the procedures inside it
SAMPLE="sample_complexity.c"
cat > "$SAMPLE" <<'EOF'
int oneline(void) { return 0; }

int branchy(int a, int b)
{
    int r = 0;
    if (a > 0) {
        if (b > 0)
            r = 1;
        else
            r = 2;
    }
    return r;
}
EOF
out=$("$BIN" -t0 "$SAMPLE" 2>&1)
rc=$?
if [ $rc -eq 0 ] && [ -n "$out" ] \
    && printf '%s' "$out" | grep -q "^Complexity Scores" \
    && printf '%s' "$out" | grep -q "branchy"; then
    echo "PASS: complexity scored $SAMPLE"
    printf '%s\n' "$out" | head -n 4
    passed=$((passed + 1))
else
    echo "FAIL: complexity scoring rc=$rc output=$out"
    failed=$((failed + 1))
fi
rm -f "$SAMPLE"

echo "RESULT: passed=$passed failed=$failed"
[ $failed -eq 0 ] || exit 1
exit 0
