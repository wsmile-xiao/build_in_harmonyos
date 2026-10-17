#!/data/service/hnp/bin/bash
set -euo pipefail

WORK="$(pwd)/_acme_test"
rm -rf "$WORK"
mkdir -p "$WORK"
cd "$WORK"

cat > hello.a <<'EOF'
* = $c000
    lda #$01
    sta $d020
    rts
EOF

acme --format plain --outfile hello.bin hello.a
test -s hello.bin

actual="$(od -An -tx1 -v hello.bin | tr -d ' \n')"
test "$actual" = "a9018d20d060"

printf '%s\n' "[test] acme assembled hello.bin"
