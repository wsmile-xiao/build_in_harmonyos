#!/bin/bash
# test_package smoke test for tlrc 1.13.1
# Verifies the tldr binary works: --version and local page rendering.
set -e

if [ -z "$TLDR_BIN" ]; then
    echo "ERROR: TLDR_BIN not set" >&2
    exit 1
fi

echo "== Test 1: tldr --version =="
"$TLDR_BIN" --version

echo "== Test 2: tldr --render local page =="
TMP_PAGE=$(mktemp)
cat > "$TMP_PAGE" <<'EOF'
# example

> Test page for tldr rendering.

- do something: `command --flag`
EOF
"$TLDR_BIN" --render "$TMP_PAGE" > /dev/null
rm -f "$TMP_PAGE"

echo "tlrc test_package: PASS"
