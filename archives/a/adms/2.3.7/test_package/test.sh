#!/bin/sh
set -eu

work="${TMPDIR:-/tmp}/adms-test-$$"
mkdir -p "$work"
trap 'rm -rf "$work"' EXIT

cat > "$work/model.va" <<'EOF'
`include "constants.vams"
`include "disciplines.vams"
module smoke(p, n);
inout p, n;
electrical p, n;
parameter real gain = 1.0;
analog V(p,n) <+ gain;
endmodule
EOF

admsXml -e "$ADMS_DATA_DIR/adms.implicit.xml" "$work/model.va"
test -s "$work/model.xml"
grep -q "module" "$work/model.xml"
echo "[test] admsXml consumer test passed"
