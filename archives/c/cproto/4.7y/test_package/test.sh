#!/bin/sh
# test_package/test.sh — Verify cproto binary works on a sample C file
# R34: test must actually use the tested package's binary

set -euo pipefail

# Create a sample C source file with a function definition
cat > /tmp/test_cproto_sample.c << 'EOF'
int add(int a, int b) {
    return a + b;
}

void greet(void) {
    printf("hello\n");
}
EOF

# Run cproto to extract prototypes (this exercises the actual binary)
output=$(cproto /tmp/test_cproto_sample.c 2>&1)

# Verify output contains expected prototypes
echo "$output"
echo "$output" | grep -q "int add(int a, int b)" || {
    echo "FAIL: expected prototype 'int add(int a, int b)' not found"
    exit 1
}
echo "$output" | grep -q "void greet(void)" || {
    echo "FAIL: expected prototype 'void greet(void)' not found"
    exit 1
}

echo "test cproto 4.7y: PASS"
