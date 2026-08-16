#!/usr/bin/env sh
set -eu

IASL=${1:?"usage: test_iasl.sh /path/to/iasl"}
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/acpica-iasl-test.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT HUP INT TERM

"$IASL" -v

cat > "$WORKDIR/test.asl" <<'EOF'
DefinitionBlock ("", "DSDT", 2, "OHPC", "ACPITEST", 0x00000001)
{
    Method (MTH0, 0, NotSerialized)
    {
        Return (0x2A)
    }
}
EOF

cd "$WORKDIR"
"$IASL" -tc test.asl
test -s test.aml

"$IASL" -d test.aml
test -s test.dsl
grep -q "MTH0" test.dsl

cp test.dsl roundtrip.dsl
"$IASL" -p roundtrip roundtrip.dsl
test -s roundtrip.aml
