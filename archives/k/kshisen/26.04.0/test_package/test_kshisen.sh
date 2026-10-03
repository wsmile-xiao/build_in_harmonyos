#!/bin/sh
# test_package runner for kshisen 26.04.0 (OHOS).
#
# Runs the packaged GUI binary headless (offscreen Qt platform, sandboxed
# HOME/XDG tree and loader path provided inline by conanfile.py test(),
# which also repairs the path-form DT_NEEDED closure and mirrors
# dependency libraries into the cwd-relative resolution bases) and
# asserts OHOS portability of the installed artifact:
#   1. `kshisen --version` exits 0 and prints the upstream version --
#      proves the musl loader resolves the complete
#      KMahjongglib6/KDEGames6/KF6/Qt6 DT_NEEDED closure through the
#      conan-provided LD_LIBRARY_PATH (explicit closure, no
#      default-search-path luck).
#   2. llvm-readelf shows no path-form DT_NEEDED entries (absolute
#      conan-cache paths or ../-relative entries, knowledge E537) in the
#      installed executable.
#   3. libKDEGames6 and libKMahjongg6 are present among the DT_NEEDED
#      entries (the game really consumes the KDE Games framework and the
#      Mahjongg tileset library from the dependency graph).
#
# The upstream movetest (N=1) already ran inside conan create's build()
# via ctest (recipe _run_upstream_tests, keditbookmarks precedent); this
# wrapper is the consumer-side complement on the packaged artifact.
set -u

EXE="$1"

fail() {
    echo "FAIL: $1"
    exit 1
}

[ -n "$EXE" ] || fail "no executable argument"
[ -f "$EXE" ] || fail "executable not found: $EXE"
[ -x "$EXE" ] || fail "executable not executable: $EXE"

# --- 1. headless consumer smoke: --version ---
VERSION_OUTPUT="$("$EXE" --version 2>&1)"
VERSION_RC=$?
echo "--- kshisen --version (rc=$VERSION_RC) ---"
echo "$VERSION_OUTPUT"
echo "----------------------------------------"

# KSHISEN_VERSION = 1.11.<release-service compact 26040>; --version prints
# "kshisen 1.11.26040" (KAboutData + QCommandLineParser).
if [ "$VERSION_RC" -eq 0 ] && echo "$VERSION_OUTPUT" | grep -q "1\.11\.26040\|26\.04"; then
    echo "[ok] --version smoke passed under offscreen Qt platform"
else
    fail "--version smoke failed (rc=$VERSION_RC)"
fi

# --- 2/3. OHOS DT_NEEDED portability assertions (E537 parity) ---
READELF=""
for candidate in llvm-readelf readelf /data/service/hnp/bin/llvm-readelf /data/service/hnp/bin/readelf; do
    if command -v "$candidate" >/dev/null 2>&1; then
        READELF="$candidate"
        break
    fi
done
[ -n "$READELF" ] || fail "no readelf tool found for DT_NEEDED assertions"

NEEDED="$("$READELF" -d "$EXE" 2>/dev/null | grep '(NEEDED)' | sed 's/.*Shared library: \[\(.*\)\].*/\1/')"
[ -n "$NEEDED" ] || fail "could not read DT_NEEDED entries from $EXE"

echo "--- DT_NEEDED entries of $(basename "$EXE") ---"
echo "$NEEDED"
echo "----------------------------------------"

PATH_FORM_NEEDED=$(echo "$NEEDED" | grep -E '^/|^\.\./' || true)
if [ -n "$PATH_FORM_NEEDED" ]; then
    fail "path-form DT_NEEDED entries leaked into the artifact: $PATH_FORM_NEEDED"
fi
echo "[ok] no path-form DT_NEEDED entries (basename closure only)"

echo "$NEEDED" | grep -q 'libKDEGames6' || fail "libKDEGames6 missing from DT_NEEDED -- package does not consume the KDEGames dependency"
echo "[ok] libKDEGames6 present in DT_NEEDED"

echo "$NEEDED" | grep -q 'libKMahjongg6' || fail "libKMahjongg6 missing from DT_NEEDED -- package does not consume the libkmahjongg dependency"
echo "[ok] libKMahjongg6 present in DT_NEEDED"

echo "PASS: kshisen consumer smoke + OHOS DT_NEEDED portability assertions OK"
exit 0
