#!/bin/sh
# test.sh — verify cppi indents C preprocessor directives correctly

set -euo pipefail

tmp_input=$(mktemp) || exit 1
tmp_output=$(mktemp) || exit 1
tmp_stdin=$(mktemp) || exit 1
trap 'rm -f "$tmp_input" "$tmp_output" "$tmp_stdin"' EXIT

# Verify binary exists and runs
cppi --version

# Create a sample C file with nested preprocessor directives
cat > "$tmp_input" << 'EOF'
#if FOO
# if BAR
#  define BAZ 1
# endif
#endif
EOF

# Run cppi on it
cppi "$tmp_input" > "$tmp_output" 2>/dev/null

# Verify output contains properly indented directives
if grep -q '#if FOO' "$tmp_output" && \
   grep -q '# if BAR' "$tmp_output" && \
   grep -q '#  define BAZ 1' "$tmp_output"; then
    echo "PASS: cppi correctly indented nested preprocessor directives"
else
    echo "FAIL: cppi output does not contain expected indentations"
    cat "$tmp_output"
    exit 1
fi

# Test stdin mode
printf '#if FOO\n# define BAR\n#endif\n' | cppi - > "$tmp_stdin" 2>/dev/null
if grep -q '# define BAR' "$tmp_stdin"; then
    echo "PASS: cppi stdin mode works"
else
    echo "FAIL: cppi stdin mode failed"
    exit 1
fi

echo "All cppi tests passed"
