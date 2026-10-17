#!/usr/bin/env bash
# Functional test for the packaged pgdbf binary.
#
# Craft a minimal dBase III fixture (NAME C(10), AGE N(3), one record
# "Café / 42" stored in LATIN-1) and assert that pgdbf emits valid
# PostgreSQL import SQL for it, including an iconv LATIN1 -> UTF-8
# conversion when -s LATIN1 is requested.
#
# Note: assertions are kept ASCII-safe (or valid UTF-8 on the iconv
# output) because the consumer test runtime may use toybox grep whose
# regex engine does not cross non-UTF-8 bytes.
set -eu
# Byte-oriented matching (DBF conversion output may contain non-UTF-8
# bytes until the requested iconv conversion is applied).
export LC_ALL=C

PGDBF="${1:-pgdbf}"
if [ -z "$PGDBF" ] || [ ! -x "$PGDBF" ]; then
    echo "pgdbf binary not found: $PGDBF" >&2
    exit 127
fi

workdir="${TMPDIR:-$PWD}/pgdbf-test-$$"
trap 'rm -rf "$workdir"' EXIT
mkdir -p "$workdir"
dbf="$workdir/sample.dbf"

# dBase III header: version 0x03, 1 record, 2 fields (NAME C10, AGE N3),
# then one record: space + 'Caf\xe9' + 6 NULs + ' 42'.
printf '\003\176\011\004\001\000\000\000\141\000\016\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\116\101\115\105\000\000\000\000\000\000\000\103\000\000\000\000\012\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\101\107\105\000\000\000\000\000\000\000\000\116\000\000\000\000\003\000\000\000\000\000\000\000\000\000\000\000\000\000\000\000\015\040\103\141\146\351\000\000\000\000\000\000\040\064\062' > "$dbf"

# 1) Default conversion: exit 0, CREATE TABLE issued, data row present
#    (raw bytes; only the ASCII prefix "Caf" is asserted here).
"$PGDBF" "$dbf" > "$workdir/out.sql" 2> "$workdir/out.err"
grep -q 'CREATE TABLE sample (name VARCHAR(10), age NUMERIC(3));' "$workdir/out.sql"
grep -q '^Caf' "$workdir/out.sql"

# 2) iconv path: -s LATIN1 must transcode 0xE9 to the UTF-8 e-acute.
#    Output is then valid UTF-8, so the full row is asserted.
"$PGDBF" -s LATIN1 "$dbf" > "$workdir/out-utf8.sql" 2> "$workdir/out-utf8.err"
grep -q 'Café' "$workdir/out-utf8.sql"
grep -q $'\t42' "$workdir/out-utf8.sql"

echo "pgdbf functional assertions passed"
