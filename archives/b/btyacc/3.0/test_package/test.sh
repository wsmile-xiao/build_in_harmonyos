#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for btyacc executable
# Runs the parser generator on a minimal grammar and verifies C parser output.
set -euo pipefail

echo "[step] btyacc smoke test"

TMPDIR_WORK=$(mktemp -d)
trap 'rm -rf "$TMPDIR_WORK"' EXIT

cat > "$TMPDIR_WORK/mini.y" <<'EOF'
%token NUM
%%
expr: expr '+' NUM | NUM ;
%%
EOF

# Generate parser (options must precede the grammar filename; btyacc writes <prefix>_tab.c/_tab.h)
if ! btyacc -d -b "$TMPDIR_WORK/out" "$TMPDIR_WORK/mini.y" > "$TMPDIR_WORK/btyacc.log" 2>&1; then
    echo "[fail] btyacc failed on minimal grammar"
    cat "$TMPDIR_WORK/btyacc.log"
    exit 1
fi

if [ ! -s "$TMPDIR_WORK/out_tab.c" ] || [ ! -s "$TMPDIR_WORK/out_tab.h" ]; then
    echo "[fail] btyacc did not produce parser output"
    exit 1
fi

echo "[ok] btyacc generated out_tab.c ($(wc -l < "$TMPDIR_WORK/out_tab.c") lines)"
echo "[ok] btyacc generated out_tab.h"