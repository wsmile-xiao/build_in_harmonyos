#!/system/bin/sh
set -eu

BMKDEP="${BMKDEP:-bmkdep}"
OHOS_TMPDIR="${OHOS_TMPDIR:-${TMPDIR:-}}"
[ -n "$OHOS_TMPDIR" ] || {
    echo "FAIL: TMPDIR must name a writable HarmonyOS sandbox directory" >&2
    exit 1
}
work_dir="$OHOS_TMPDIR/bmkdep-harmonyos-test-$$"

fail()
{
    echo "FAIL: $*" >&2
    exit 1
}

case "$(param get const.ohos.fullname 2>/dev/null || true)" in
    OpenHarmony-*) ;;
    *) fail "this test must run on an OpenHarmony target" ;;
esac

[ -x "$BMKDEP" ] || fail "bmkdep is not executable: $BMKDEP"
[ -d "$OHOS_TMPDIR" ] || fail "HarmonyOS temporary directory is missing"
[ -w "$OHOS_TMPDIR" ] || fail "HarmonyOS temporary directory is not writable"

mkdir -p "$work_dir/bin" "$work_dir/include"
trap 'rm -rf "$work_dir"' EXIT HUP INT TERM

printf '#define BMKDEP_OHOS_VALUE 42\n' > "$work_dir/include/sample.h"
printf '#include "include/sample.h"\nint main(void) { return BMKDEP_OHOS_VALUE; }\n' \
    > "$work_dir/sample.c"

cat > "$work_dir/bin/clang" <<'EOF'
#!/system/bin/sh
printf 'sample.o: ./sample.c ./include/sample.h\n'
EOF
chmod +x "$work_dir/bin/clang"

(
    cd "$work_dir"
    unset CC
    TMPDIR="$OHOS_TMPDIR" PATH="$work_dir/bin:/system/bin" \
        "$BMKDEP" -f depend sample.c
)

actual="$(sed 's/[[:space:]][[:space:]]*/ /g; s/[[:space:]]*$//' \
    "$work_dir/depend")"
[ "$actual" = 'sample.o: sample.c include/sample.h' ] || \
    fail "HarmonyOS default compiler/sandbox-temp flow produced: $actual"

echo "PASS: HarmonyOS default clang with writable sandbox TMPDIR (1 assertion)"
