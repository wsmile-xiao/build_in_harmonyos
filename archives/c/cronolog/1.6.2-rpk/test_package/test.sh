# test_package/test.sh — functional smoke test for the cronolog executable.
# Runs inside the conanrun env (PATH includes the installed bin/).
#
# cronolog semantics: it copies stdin to a date-templated log file and exits
# with code 3 on stdin EOF — that is its *normal* termination, not a failure.
# Each piped stage below therefore masks exit 3 explicitly; any other
# non-zero code fails the test (set -euo pipefail stays on).
set -eu
set -o pipefail 2>/dev/null || true

# Absolute binary path injected by conanfile (package_folder/bin or sbin).
# Falls back to PATH lookup for local runs. Never rely on conanrun PATH
# alone: preflight evidence showed PATH without any conan-home entry.
CRONOLOG="${CRONOLOG_BIN:-cronolog}"
echo "[test] binary: $CRONOLOG"

# Test 1: binary executes and reports its version (-V prints to stderr).
# NOTE: avoid `| grep -qi` here — minimal OHOS grep/pipefail variants make
# the pipeline fragile. Use POSIX shell builtins only (capture + case).
echo "[test] cronolog -V"
if [ -n "${CRONOLOG_BIN:-}" ]; then
    test -x "$CRONOLOG" || {
        echo "cronolog binary not executable: $CRONOLOG"
        exit 1
    }
else
    command -v "$CRONOLOG" || {
        echo "cronolog not found on PATH=$PATH"
        exit 1
    }
fi
set +e
VEROUT="$("$CRONOLOG" -V 2>&1)"
VERC=$?
set -e
echo "[test] cronolog -V exit=$VERC out=[$VEROUT]"
if [ "$VERC" -ne 0 ]; then
    echo "cronolog -V exited $VERC"
    exit 1
fi
case "$VEROUT" in
    *[Cc][Rr][Oo][Nn][Oo][Ll][Oo][Gg]*|*1.6.2*|*[Vv][Ee][Rr][Ss][Ii][Oo][Nn]*)
        ;;
    *)
        echo "cronolog -V did not report a version"
        exit 1
        ;;
esac
echo "version check OK"

# NOTE: /tmp is read-only on OHOS — use $TMPDIR for the scratch dir.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/cronolog-test-$$"
rm -rf "$TESTDIR"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

printf 'cronolog line one\ncronolog line two\ncronolog line three\n' > "$TESTDIR/input.log"

# Test 2: once-only write (-o skips rotation) lands byte-identical content.
echo "[test] cronolog -o (once-only write)"
set +e
printf 'cronolog line one\ncronolog line two\ncronolog line three\n' \
    | "$CRONOLOG" -o "$TESTDIR/once.log"
rc=$?
set -e
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "❌ cronolog -o failed with exit $rc"
    exit 1
fi
test -s "$TESTDIR/once.log" || {
    echo "❌ cronolog -o did not produce the output file"
    exit 1
}
cmp -s "$TESTDIR/input.log" "$TESTDIR/once.log" || {
    echo "❌ once-only output differs from input"
    exit 1
}
echo "✅ once-only content identical"

# Test 3: date template auto-creates subdirectories with identical content.
echo "[test] cronolog date-template (subdir creation)"
TEMPLATE="$TESTDIR/logs/%Y/%m/%d/app.log"
set +e
printf 'cronolog line one\ncronolog line two\ncronolog line three\n' \
    | "$CRONOLOG" "$TEMPLATE"
rc=$?
set -e
if [ "$rc" -ne 0 ] && [ "$rc" -ne 3 ]; then
    echo "❌ templated cronolog failed with exit $rc"
    exit 1
fi
ROTATED="$(find "$TESTDIR/logs" -name app.log -type f | head -n 1)"
test -n "$ROTATED" || {
    echo "❌ templated log file was not created under $TESTDIR/logs"
    find "$TESTDIR" | head -n 20
    exit 1
}
cmp -s "$TESTDIR/input.log" "$ROTATED" || {
    echo "❌ templated output differs from input"
    exit 1
}
echo "✅ template subdirs + content OK ($ROTATED)"
