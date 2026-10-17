#!/bin/sh
# test_package runner for tl-parser.
#
# Real consumer test of the installed tl-parser binary: parse a TL schema
# fixture and require a non-empty serialized .tlo file.
#
# NOTE: tl-parser returns exit 0 for some parse failures, so we must assert
# on the produced .tlo output (existence + non-empty), not only on the exit
# code. A syntactically broken schema produces no .tlo at all.
set -eu

cat > schema.tl <<'EOF'
boolFalse#bc799737 = Bool;
boolTrue#997275b5 = Bool;
true#3fedd339 = True;
EOF

tl-parser -e out.tlo schema.tl

test -f out.tlo
test -s out.tlo

echo "[ok] tl-parser produced a non-empty .tlo file from the TL schema fixture"
