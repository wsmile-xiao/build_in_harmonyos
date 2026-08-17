#!/bin/bash
# test_package/test.sh -- Dune 3.17.0 consumer test
# Verifies dune binary is functional
set -euo pipefail

DUNE_BIN="${1:-dune}"

echo "=== Dune version check ==="
"$DUNE_BIN" --version

echo "=== Dune build check ==="
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT
cd "$TMPDIR"
mkdir -p src
cat > dune-project << EOF
(lang dune 3.0)
(name test_project)
EOF
cat > src/dune << EOF
(executable
 (name test_main)
 (public_name test_project.test_main))
EOF
cat > src/test_main.ml << EOF
let () = print_endline "Hello from Dune!"
EOF
"$DUNE_BIN" build
echo "Build succeeded"

echo "=== Run built executable ==="
OUT=$("$DUNE_BIN" exec ./src/test_main.exe 2>/dev/null || "$DUNE_BIN" exec ./test_main.exe 2>/dev/null || true)
echo "Output: $OUT"
if [ "$OUT" = "Hello from Dune!" ]; then
    echo "Executable ran successfully"
else
    echo "ERROR: built executable output mismatch: '$OUT'" >&2
    exit 1
fi

echo "=== All tests passed ==="
cd /
rm -rf "$TMPDIR"
