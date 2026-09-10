#!/usr/bin/env sh
set -eu

: "${TMPDIR:=$PWD/.tmp}"
export TMPDIR

BMKDEP="${BMKDEP:-bmkdep}"
assertion_count=5
work_dir="$TMPDIR/bmkdep-test-$$"
mkdir -p "$work_dir"
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

normalize()
{
    sed 's/[[:space:]][[:space:]]*/ /g; s/[[:space:]]*$//' "$1"
}

printf 'sample.o: ./sample.c ./include/sample.h\n' > "$work_dir/sample.d"

"$BMKDEP" -d -f "$work_dir/depend" "$work_dir/sample.d"
actual="$(normalize "$work_dir/depend")"
[ "$actual" = 'sample.o: sample.c include/sample.h' ] || \
    fail "dependency normalization mismatch: $actual"

"$BMKDEP" -d -P 'obj/' -s '.o,.po' -f "$work_dir/prefixed" \
    "$work_dir/sample.d"
actual="$(normalize "$work_dir/prefixed")"
case "$actual" in
    'obj/sample.o obj/sample.po: sample.c include/sample.h'|\
    'obj/sample.po obj/sample.o: sample.c include/sample.h') ;;
    *) fail "prefix/suffix expansion mismatch: $actual" ;;
esac

"$BMKDEP" -d -p -f "$work_dir/program" "$work_dir/sample.d"
actual="$(normalize "$work_dir/program")"
[ "$actual" = 'sample: sample.c include/sample.h' ] || \
    fail "program-mode target mismatch: $actual"

"$BMKDEP" -d -a -f "$work_dir/program" "$work_dir/sample.d"
line_count="$(wc -l < "$work_dir/program")"
line_count="${line_count##*[!0-9]}"
[ "$line_count" = '2' ] || fail "append mode wrote $line_count lines, expected 2"

"$BMKDEP" -d -i -f "$work_dir/included" "$work_dir/sample.d"
actual="$(normalize "$work_dir/included")"
[ "$actual" = ".-include \"$work_dir/sample.d\"" ] || \
    fail "include mode mismatch: $actual"

if [ "${BMKDEP_SKIP_COMPILER:-0}" != '1' ]; then
    printf '#define BMKDEP_TEST_VALUE 42\n' > "$work_dir/compile.h"
    printf '#include "compile.h"\nint main(void) { return BMKDEP_TEST_VALUE; }\n' \
        > "$work_dir/compile.c"
    (
        cd "$work_dir"
        "$BMKDEP" -f compiler.depend -- -I. compile.c
    )
    actual="$(normalize "$work_dir/compiler.depend")"
    case "$actual" in
        *compile.h*) ;;
        *) fail "compiler mode did not discover compile.h: $actual" ;;
    esac
    assertion_count=6
else
    echo "SKIP: compiler-invocation assertion (no compiler installed on target)"
fi

echo "PASS: bmkdep dependency processing ($assertion_count assertions)"
