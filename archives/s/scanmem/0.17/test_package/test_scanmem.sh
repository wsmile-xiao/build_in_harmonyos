#!/bin/sh
# test_scanmem.sh -- consumer-side functional tests for the packaged scanmem.
#
# Driven by test_package/conanfile.py test() through the profile's bash (OHOS
# has no /bin/sh guarantee; bash/5.3 test_package precedent).
#
# Eight checks. The counters live in this script and the last line prints
# HMBS_TEST_PACKAGE_RESULT, so the rule4 gate reads real numbers instead of
# scraping stdout.
#
#   t1 scanmem --version carries the package version
#   t2 scanmem --help prints the documented usage
#   t3 invalid pid is rejected                       (negative test)
#   t4 scanmem finds a known sentinel in a live process
#   t5 snapshot -> set -> delete round-trip
#   t6 257-entry wildcard bytearray scan (chunked scan path)
#   t7 libscanmem.so.1 loads and exports sm_/show_ API   [HarmonyOS-specific]
#   t8 packaged layout: bin/ + lib/ + headers present    [HarmonyOS-specific]
#
# NOTE on `set`: -u and pipefail are on, -e is deliberately OFF. This is a
# counting harness; an early exit would suppress the marker line and hide the
# discovered/passed figures the gate needs.

set -u
set -o pipefail 2>/dev/null || true

TOTAL=8
PASSED=0

SENTINEL_HEX=0x0BADF00D
# 0x0BADF00D = 11*16777216 + 10*1048576 + 13*65536 + 15*4096 + 13
SENTINEL_DEC=195948557

BASE_TMP="${TMPDIR:-/tmp}"
WORK="$(mktemp -d "$BASE_TMP/scanmem_test_XXXXXX")" || exit 1
TARGET_PID=""

cleanup() {
    [ -n "$TARGET_PID" ] && kill "$TARGET_PID" 2>/dev/null
    rm -rf "$WORK"
}
trap cleanup EXIT INT TERM

pass() { echo "PASS $1 $2"; PASSED=$((PASSED + 1)); }
fail() {
    echo "FAIL $1 $2"
    [ -n "${3:-}" ] && { echo "  --- output ---"; sed -n '1,25p' "$3"; }
}

# ---------------------------------------------------------------- t1 version
# main.c: printversion() writes "scanmem version <PACKAGE_VERSION>" to stderr
# and then exit(EXIT_FAILURE), so the exit code is 1 by design. The command is
# therefore run *unconditionally* and the verdict comes from grep alone: using
# `scanmem --version && grep ...` would short-circuit on the non-zero exit and
# fail the check even though the version string was printed correctly. (This is
# also what keeps CI's L2 --version probe honest: L2 sees a non-zero exit and
# reports a non-blocking warn.)
scanmem --version > "$WORK/version.txt" 2>&1
if grep -q "scanmem version 0\.17" "$WORK/version.txt"; then
    pass t1 version_string
else
    fail t1 version_string "$WORK/version.txt"
fi

# ------------------------------------------------------------------- t2 help
# main.c: help_text literal, printed after printcopyright(). Same exit-1 caveat
# as t1, so the run is not chained with &&.
scanmem --help > "$WORK/help.txt" 2>&1
if grep -q "Usage: scanmem" "$WORK/help.txt" \
    && grep -q -- "--pid=pid" "$WORK/help.txt" \
    && grep -q -- "--command" "$WORK/help.txt"; then
    pass t2 help_usage
else
    fail t2 help_usage "$WORK/help.txt"
fi

# ------------------------------------------------------- t3 invalid pid (neg)
# main.c parse_parameters(): pid 0 is rejected with "invalid pid specified."
if scanmem -p 0 -c "exit" > "$WORK/badpid.txt" 2>&1; then
    fail t3 reject_invalid_pid
else
    if grep -q "invalid pid" "$WORK/badpid.txt"; then
        pass t3 reject_invalid_pid
    else
        fail t3 reject_invalid_pid "$WORK/badpid.txt"
    fi
fi

# ------------------------------------------------------- start scan target
./scanmem_target > "$WORK/target.out" 2>"$WORK/target.err" &
TARGET_PID=$!
# Wait for the helper to print its PID and settle into pause().
i=0
while [ $i -lt 50 ]; do
    TARGET_PID=$(head -1 "$WORK/target.out" 2>/dev/null)
    [ -n "$TARGET_PID" ] && break
    i=$((i + 1))
    sleep 0.1 2>/dev/null || sleep 1
done

if [ -z "$TARGET_PID" ]; then
    echo "FAIL target_startup -- helper produced no PID"
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":false,\"passed\":false,\"command\":\"sh test_scanmem.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED,\"reason\":\"scanmem_target did not start; cannot run the memory-scan checks\"}"
    exit 1
fi
echo "target pid $TARGET_PID"

# ------------------------------------------------------------ t4 find sentinel
# handler__list() returns false when num_matches == 0, and -e turns that into
# a non-zero exit, so exit 0 here really does mean "the scanner found it".
if scanmem -p "$TARGET_PID" -e \
    -c "option scan_data_type int32;$SENTINEL_DEC;list 5;exit" \
    > "$WORK/find.txt" 2>&1; then
    if grep -qi "no matches are known" "$WORK/find.txt"; then
        fail t4 find_sentinel "$WORK/find.txt"
    else
        pass t4 find_sentinel
    fi
else
    fail t4 find_sentinel "$WORK/find.txt"
fi

# ------------------------------------------- t5 snapshot / set / delete cycle
# Mirrors upstream test/sm_test.sh cases 3-4:
#   option scan_data_type int8;snapshot;1;exit
#   option scan_data_type int8;1;delete 0;1;exit
if scanmem -p "$TARGET_PID" -e \
    -c "option scan_data_type int32;$SENTINEL_DEC;snapshot;1;exit" \
    > "$WORK/snap.txt" 2>&1 \
   && scanmem -p "$TARGET_PID" -e \
    -c "option scan_data_type int32;1;delete 0;1;exit" \
    > "$WORK/del.txt" 2>&1; then
    pass t5 snapshot_delete
else
    fail t5 snapshot_delete "$WORK/snap.txt"
fi

# ------------------------------------- t6 257-entry wildcard bytearray scan
# 257 is upstream's deliberate choice: it forces the full/chunked scan routine
# instead of the short-buffer fast path. Builds a bytearray of 00 ?? pairs.
BA=""
S=""
j=0
while [ $j -lt 257 ]; do
    BA="$BA 00 ?? "
    S="${S}a"
    j=$((j + 1))
done
if scanmem -p "$TARGET_PID" -e \
    -c "option scan_data_type bytearray;$BA;exit" \
    > "$WORK/ba.txt" 2>&1; then
    pass t6 bytearray_wildcard
else
    fail t6 bytearray_wildcard "$WORK/ba.txt"
fi

# -------------------------------------- t7 packaged library API [OHOS]
# Two independent proofs that the packaged libscanmem is usable on the target:
#   check_api        -> compiled+linked against include/ + lib/ (link-time
#                       symbols resolved by the OHOS linker/loader)
#   check_libscanmem -> dlopen/dlsym of libscanmem.so.1 (run-time resolution,
#                       proves the libtool -export-symbols-regex '^sm_|^show_'
#                       version script kept the public API exported)
# The link-time half is also what makes CI's L1e negative test meaningful:
# with include/ and lib/ moved away, build() cannot link and the test fails.
if ./check_api > "$WORK/api.txt" 2>&1 \
    && grep -q "APICHECK version=0\.17" "$WORK/api.txt" \
    && grep -q "libscanmem version 0\.17" "$WORK/api.txt" \
    && ./check_libscanmem libscanmem.so.1 > "$WORK/lib.txt" 2>&1 \
    && grep -q "LIBCHECK dlopen=ok" "$WORK/lib.txt" \
    && grep -q "LIBCHECK sm_get_version=present" "$WORK/lib.txt" \
    && grep -q "LIBCHECK sm_printversion=present" "$WORK/lib.txt" \
    && grep -q "libscanmem version 0\.17" "$WORK/lib.txt"; then
    pass t7 libscanmem_exports
else
    fail t7 libscanmem_exports "$WORK/api.txt"
    sed -n '1,10p' "$WORK/lib.txt" 2>/dev/null
fi

# ------------------------------------------------- t8 packaged layout [OHOS]
# The conan package must carry the CLI, the shared object and the public
# headers; a build that silently dropped any of them would still pass t1-t6.
# SCANMEM_PKG_ROOT is exported by test_package/conanfile.py from the real
# dependency package folder -- the test must not assume the package sits at
# "..", which is the recipe version directory, not the package.
PKG_ROOT="${SCANMEM_PKG_ROOT:-..}"
if [ -x "$PKG_ROOT/bin/scanmem" ] \
    && [ -f "$PKG_ROOT/lib/libscanmem.so.1" ] \
    && [ -f "$PKG_ROOT/include/scanmem/scanmem.h" ]; then
    pass t8 packaged_layout
else
    echo "FAIL t8 packaged_layout (pkg root: $PKG_ROOT)"
    ls -la "$PKG_ROOT/bin" "$PKG_ROOT/lib" "$PKG_ROOT/include/scanmem" 2>&1 | sed -n '1,20p'
fi

echo "Results: $PASSED/$TOTAL consumer checks passed"
if [ "$PASSED" -eq "$TOTAL" ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"sh test_scanmem.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
    exit 0
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"sh test_scanmem.sh\",\"discovered\":$TOTAL,\"passedCount\":$PASSED}"
    exit 1
fi
