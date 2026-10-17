#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for the libkcapi command line tools.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

# 1) All four tools must be on PATH and executable.
for tool in kcapi-dgst kcapi-enc kcapi-rng kcapi-hasher; do
    command -v "$tool" >/dev/null || { echo "$tool is not on PATH"; exit 1; }
    echo "        [ok] $tool found on PATH"
done

# 2) Version contract.  Upstream prints the version and exits 0:
#    kcapi-dgst/--version, kcapi-enc/--version, kcapi-rng/--version
#    (fprintf(stderr, "Version %s\n") then exit(0)) and
#    kcapi-hasher/-v (version() then ret = 0).  Only the user space
#    kcapi_versionstring() API is involved - no AF_ALG socket.
for tool in kcapi-dgst kcapi-enc kcapi-rng; do
    echo "[test] $tool --version"
    VERSION_OUT="$("$tool" --version 2>&1)"
    case "$VERSION_OUT" in
        *1.5.0*) echo "        [ok] $VERSION_OUT" ;;
        *) echo "$tool --version did not report 1.5.0: $VERSION_OUT"; exit 1 ;;
    esac
done
echo "[test] kcapi-hasher -v"
HASH_OUT="$(kcapi-hasher -v 2>&1)"
case "$HASH_OUT" in
    *1.5.0*) echo "        [ok] $HASH_OUT" ;;
    *) echo "kcapi-hasher -v did not report 1.5.0: $HASH_OUT"; exit 1 ;;
esac
# --version long option must work on the hasher as well ("version" maps to -v).
HASH_OUT="$(kcapi-hasher --version 2>&1)"
case "$HASH_OUT" in
    *1.5.0*) echo "        [ok] kcapi-hasher --version: $HASH_OUT" ;;
    *) echo "kcapi-hasher --version did not report 1.5.0: $HASH_OUT"; exit 1 ;;
esac

# 3) Upstream --help contract: usage() ends in exit(1) for the three
#    getopt_long tools - the help text is an error path by design.
#    Regression guard: our toolchain must not have "fixed" that silently.
for tool in kcapi-dgst kcapi-enc kcapi-rng; do
    echo "[test] $tool --help (expect exit 1 with usage text)"
    set +e
    "$tool" --help >/dev/null 2>&1
    HELP_RC=$?
    set -e
    [ "$HELP_RC" -eq 1 ] || { echo "$tool --help exited $HELP_RC, want 1 (upstream contract)"; exit 1; }
    echo "        [ok] --help exit status 1"
done

# 4) Self-containment: the tools link the in-tree libkcapi statically
#    (recipe has no requirements()), so no binary may carry a DT_NEEDED
#    entry for libkcapi.
READELF="$(command -v llvm-readelf || command -v readelf || true)"
if [ -n "$READELF" ]; then
    for tool in kcapi-dgst kcapi-enc kcapi-rng kcapi-hasher; do
        echo "[test] $tool dynamic section must not reference libkcapi"
        if "$READELF" -d "$(command -v "$tool")" 2>/dev/null | grep -q 'libkcapi'; then
            echo "$tool still has a DT_NEEDED entry for libkcapi"
            exit 1
        fi
    done
    echo "        [ok] all tools are self-contained"
fi

# 5) Negative control: unknown options must not be reported as success
#    (getopt_long default branch -> usage() -> exit(1)).
echo "[test] unknown option (expected failure)"
set +e
kcapi-dgst --bogus-option >/dev/null 2>&1
RC=$?
set -e
[ "$RC" -ne 0 ] || { echo "kcapi-dgst accepted the unknown option --bogus-option"; exit 1; }
echo "        [ok] unknown option rejected (exit $RC)"

# 6) The four tools must be loadable ELF binaries with a .codesign section
#    (the OHOS SDK clang emits one by default; a package built with a
#    stripped-down toolchain would not load on device).
if [ -n "$READELF" ]; then
    for tool in kcapi-dgst kcapi-enc kcapi-rng kcapi-hasher; do
        if "$READELF" -S "$(command -v "$tool")" 2>/dev/null | grep -q codesign; then
            echo "        [ok] $tool carries a .codesign section"
        else
            echo "$tool has no .codesign section (would not load on HarmonyOS)"
            exit 1
        fi
    done
fi

echo "All tests passed."
