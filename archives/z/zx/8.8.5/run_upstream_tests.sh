#!/bin/sh
# run_upstream_tests.sh - zx 8.8.5 upstream test runner (HarmonyOS PC / OHOS).
#
# Usage:  sh run_upstream_tests.sh <source-root> [reports-dir]
#
#   $1  source root of zx 8.8.5 (contains test/, build/, node_modules/)
#   $2  optional reports directory (defaults to <source-root>/.zx-test-reports)
#
# Behaviour
# ---------
# This runner EXECUTES THE COMPLETE UPSTREAM SUITE, unmodified: no test is
# deleted, rewritten or skipped. It runs every test file individually with
# `node --test`, one process at a time (--test-concurrency=1 - this device has
# almost no free swap), writes a TAP log per file and prints a machine-readable
# tally:
#
#   UPSTREAM_TESTS_FILE <key> tests=<N> pass=<N> fail=<N> skipped=<N>
#   UPSTREAM_TESTS_SUMMARY total=<N> pass=<N> fail=<N> skipped=<N> files=<N>
#
# Policy (which failures are tolerated) is NOT applied here: conanfile.py
# parses these TAP logs and fails the build on any failure that is not in its
# documented EXPECTED_ENV_FAILURES allowlist. Keeping the policy in the recipe
# means the runner has exactly one job - run everything and report honestly.
# Exit code is 0 as soon as all 12 files produced a test summary; a non-zero
# exit therefore means the harness itself broke (missing compiler, crashed
# node), not that an assertion failed.
#
# ---------------------------------------------------------------------------
# Why per-file invocation instead of `test/all.test.js`
# ---------------------------------------------------------------------------
# all.test.js is only the aggregate entry point; running the files one at a
# time produces per-file pass/fail evidence (R51: inventory the upstream tests,
# actually run them, report the measured numbers truthfully). The 12 files
# below are the complete default unit suite (`npm run test:unit`):
#   8 JS files : cli core deps export global index util vendor
#   4 TS files : error log md goods   (compiled to JS first, see below)
# extra.test.js is a license-header lint and all.test.js is the aggregate entry
# point - neither is part of the default unit suite.
#
# ---------------------------------------------------------------------------
# Reporters
# ---------------------------------------------------------------------------
# The `dot` reporter goes to stdout (visible in the conan build log) while the
# `tap` reporter is written to reports/<file>.log because TAP emits exactly the
# `# tests` / `# pass` / `# fail` / `# skipped` summary lines that both this
# script and conanfile.py parse.
#
# `--test-force-exit` is required: several upstream tests leave listening
# sockets / child handles open, so the runner process otherwise never exits
# after the suite finishes (measured: cli.test.js completes and then hangs).
#
# ---------------------------------------------------------------------------
# TypeScript test files
# ---------------------------------------------------------------------------
# `node --jitless` disables WebAssembly, so node's built-in TypeScript
# transform (amaro/WASM) cannot be used. The four .ts test files are compiled
# first with the bundled typescript compiler (a devDependency):
#
#   node --jitless node_modules/typescript/lib/tsc.js \
#       --allowImportingTsExtensions --rewriteRelativeImportExtensions \
#       --module nodenext --target es2022 --moduleResolution nodenext \
#       --skipLibCheck --outDir <outdir> test/{error,log,md,goods}.test.ts
#
# tsc reports the project's own pre-existing type diagnostics but emits the JS
# anyway; the runner only requires that <outdir>/test/*.js AND <outdir>/src/*.js
# were produced (the emitted tests import ../src/*.js). The upstream root
# package.json is copied into <outdir> because goods.test.ts derives
# `root = resolve(__dirname, '..')` and reads `<root>/package.json`.
#
# ---------------------------------------------------------------------------
# Environment
# ---------------------------------------------------------------------------
#  * NODE_OPTIONS=--jitless --no-deprecation is mandatory: node v24.13.0 aborts
#    with `Signal 5 (core dumped)` (Check failed: 12 == (*__errno_location()))
#    without --jitless. --no-deprecation keeps node warnings out of stderr.
#  * FORCE_COLOR=1: the device terminal is TERM=dumb, so chalk disables colour
#    and the upstream colour assertions (export.test.js `core exports`,
#    log.test.ts `cmd`/`cd`/`fetch`/`retry`) fail. Upstream assumes a
#    colour-capable terminal; FORCE_COLOR restores exactly that capability
#    instead of deleting the assertions (verified: those pass with it, fail
#    without it).
#  * A `whoami` shim directory is prepended to PATH. /system/bin/whoami exists
#    but every exec fails with "whoami: bad uid" (the OHOS passwd database has
#    no record for the app uid), so test/fixtures/markdown.md.mjs
#    (`await $`whoami``) dies with exit 127 and takes `supports `--quiet` flag`
#    + `markdown scripts are working` down with it. The shim supplies the same
#    user-name string a working coreutil would (verified: both pass with it).
#  * OHOS container variables (ubsanEnabled/hwasanEnabled/UBSAN_OPTIONS/
#    OHOS_SOCKET_AppSpawn/AppSpawnCheckUnexpectedExitCall/ALACRITTY_WINDOW_ID)
#    are unset before node runs - inherited they crash node (same workaround as
#    the alexjs / acorn / aicommit2 precedents).
# ---------------------------------------------------------------------------

set -u

SRC="${1:-}"
REPORTS="${2:-}"

if [ -z "$SRC" ]; then
    echo "usage: sh run_upstream_tests.sh <source-root> [reports-dir]" >&2
    exit 2
fi
if [ ! -d "$SRC" ]; then
    echo "source root not found: $SRC" >&2
    exit 2
fi

cd "$SRC" || exit 2

if [ -n "$REPORTS" ]; then
    :
else
    REPORTS="$SRC/.zx-test-reports"
fi
mkdir -p "$REPORTS" || exit 2

NODE_BIN="${ZX_NODE:-node}"
if ! command -v "$NODE_BIN" >/dev/null 2>&1; then
    echo "node executable not found: $NODE_BIN" >&2
    exit 2
fi

TMPDIR="${TMPDIR:-/storage/Users/currentUser/tmp}"
export TMPDIR
mkdir -p "$TMPDIR" 2>/dev/null || true

NODE_OPTIONS="--jitless --no-deprecation"
export NODE_OPTIONS

FORCE_COLOR="${FORCE_COLOR:-1}"
export FORCE_COLOR

unset ubsanEnabled 2>/dev/null || true
unset hwasanEnabled 2>/dev/null || true
unset UBSAN_OPTIONS 2>/dev/null || true
unset OHOS_SOCKET_AppSpawn 2>/dev/null || true
unset AppSpawnCheckUnexpectedExitCall 2>/dev/null || true
unset ALACRITTY_WINDOW_ID 2>/dev/null || true

# whoami shim (see "Environment" above). Kept next to the reports so nothing
# lands in the shared /tmp (read-only erofs mount on this device).
SHIM_DIR="$REPORTS/.zx-shim"
mkdir -p "$SHIM_DIR" 2>/dev/null || true
if [ ! -x "$SHIM_DIR/whoami" ]; then
    printf '#!/bin/sh\necho "${USER:-openharmony}"\n' > "$SHIM_DIR/whoami" 2>/dev/null || true
    chmod +x "$SHIM_DIR/whoami" 2>/dev/null || true
fi
if [ -x "$SHIM_DIR/whoami" ]; then
    PATH="$SHIM_DIR:$PATH"
    export PATH
    echo "[zx-tests] whoami shim active ($SHIM_DIR/whoami)"
fi

# ---------------------------------------------------------------------------
# Compile the four TypeScript test files
# ---------------------------------------------------------------------------
TSOUT="$SRC/.zx-upstream-tsout"
rm -rf "$TSOUT"
mkdir -p "$TSOUT"

TSC="$SRC/node_modules/typescript/lib/tsc.js"
if [ ! -f "$TSC" ]; then
    echo "FATAL: bundled typescript not found at $TSC (npm install --include=dev missing?)" >&2
    exit 1
fi

echo "[zx-tests] compiling TypeScript test files with tsc"
"$NODE_BIN" "$TSC" \
    --allowImportingTsExtensions --rewriteRelativeImportExtensions \
    --module nodenext --target es2022 --moduleResolution nodenext \
    --skipLibCheck --outDir "$TSOUT" \
    test/error.test.ts test/log.test.ts test/md.test.ts test/goods.test.ts \
    >"$REPORTS/tsc.log" 2>&1
echo "[zx-tests] tsc exit=$? (type diagnostics are expected; only the emitted JS matters)"

if [ ! -f "$TSOUT/test/error.test.js" ] || [ ! -f "$TSOUT/src/core.js" ]; then
    echo "FATAL: tsc did not emit the compiled test/src tree under $TSOUT" >&2
    tail -40 "$REPORTS/tsc.log" >&2
    exit 1
fi
# goods.test.ts derives root = resolve(__dirname,'..') and reads <root>/package.json
cp "$SRC/package.json" "$TSOUT/package.json"

# ---------------------------------------------------------------------------
# Run every file
# ---------------------------------------------------------------------------
FILES="cli core deps export global index util vendor error goods log md"
EXPECTED_FILES=12

files_run=0
files_ok=0
total_tests=0
total_pass=0
total_fail=0
total_skipped=0

run_file() {
    # $1 = source-relative test path, $2 = TAP log path
    "$NODE_BIN" --test --test-concurrency=1 --test-force-exit \
        --test-reporter=dot --test-reporter-destination=stdout \
        --test-reporter=tap --test-reporter-destination="$2" \
        "$1"
}

count_from_log() {
    # $1 = TAP log, $2 = field (tests|pass|fail|skipped)
    sed -n "s/^# $2 \([0-9][0-9]*\).*/\1/p" "$1" | tail -1
}

run_one() {
    key="$1"
    path="$2"

    case "$key" in
        cli|core|deps|export|global|index|util|vendor) rel="test/$key.test.js" ;;
        *) rel="$path" ;;
    esac

    log="$REPORTS/$key.log"
    : >"$log"

    echo "[zx-tests] === $key ($rel) ==="
    # Exactly one run per file: the result is deterministic and reproducible,
    # and a single pass keeps the suite inside the CI build timeout (a retry
    # was measured to double the runtime - deps alone took ~24 min - and did
    # not reliably improve the outcome, so it was removed).
    run_file "$rel" "$log"
    rc=$?

    tests=$(sed -n 's/^# tests \([0-9][0-9]*\).*/\1/p' "$log" | tail -1)
    pass=$(sed -n 's/^# pass \([0-9][0-9]*\).*/\1/p' "$log" | tail -1)
    fail=$(sed -n 's/^# fail \([0-9][0-9]*\).*/\1/p' "$log" | tail -1)
    nskip=$(sed -n 's/^# skipped \([0-9][0-9]*\).*/\1/p' "$log" | tail -1)
    [ -n "$nskip" ] || nskip=0

    files_run=$((files_run + 1))

    if [ -z "$tests" ]; then
        # The file crashed before producing results - never report silently.
        echo "UPSTREAM_TESTS_FILE $key tests=0 pass=0 fail=1 skipped=0 status=ERROR"
        echo "[zx-tests] ERROR: $key produced no test summary (rc=$rc); see $log"
        total_fail=$((total_fail + 1))
        return 0
    fi

    files_ok=$((files_ok + 1))
    echo "UPSTREAM_TESTS_FILE $key tests=$tests pass=$pass fail=$fail skipped=$nskip"
    echo "[zx-tests] $key: tests=$tests pass=$pass fail=$fail skipped=$nskip rc=$rc"

    total_tests=$((total_tests + tests))
    total_pass=$((total_pass + pass))
    total_fail=$((total_fail + fail))
    total_skipped=$((total_skipped + nskip))
    return 0
}

for key in $FILES; do
    case "$key" in
        error|log|md|goods)
            run_one "$key" "$TSOUT/test/$key.test.js" ;;
        *)
            run_one "$key" "test/$key.test.js" ;;
    esac
done

echo
echo "UPSTREAM_TESTS_SUMMARY total=$total_tests pass=$total_pass fail=$total_fail skipped=$total_skipped files=$files_run"
echo "[zx-tests] TAP logs: $REPORTS"
echo "[zx-tests] policy is applied by conanfile.py (EXPECTED_ENV_FAILURES allowlist)"

if [ "$files_run" -ne "$EXPECTED_FILES" ]; then
    echo "[zx-tests] FAIL: expected $EXPECTED_FILES files, ran $files_run" >&2
    exit 1
fi
if [ "$files_ok" -ne "$EXPECTED_FILES" ]; then
    echo "[zx-tests] FAIL: only $files_ok/$EXPECTED_FILES files produced a test summary" >&2
    exit 1
fi

echo "[zx-tests] OK: the complete upstream suite ran ($total_tests test cases)"
exit 0
