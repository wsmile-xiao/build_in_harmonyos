#!/usr/bin/env bash
set -euo pipefail
KREP_BIN="$1"
WORK_DIR="$2"
TEST_FILE="$WORK_DIR/krep-smoke.txt"

cat > "$TEST_FILE" <<'EOF'
alpha
beta
needle
EOF

"$KREP_BIN" --version
"$KREP_BIN" needle "$TEST_FILE"
"$KREP_BIN" -c needle "$TEST_FILE"
