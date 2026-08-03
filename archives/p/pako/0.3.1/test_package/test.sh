#!/bin/sh
# test_package test.sh — pako consumer test + upstream mocha suite.
#
# Phase 1 (consumer): require the packaged pako module and round-trip a
# string through deflate/inflate. Emit HMBS_TEST_PACKAGE_RESULT.
#
# Phase 2 (upstream): run the full pako mocha suite. The patched
# source tree lives under the (read-only) CONAN_PACKAGE_FOLDER_pako/
# res/pako/. We copy the test/ tree, index.js, lib/, package.json
# into a writable work directory, install the mocha devDependencies
# there, and run the suite with the same invocation pako's Makefile
# uses (mocha.opts: -R spec -t 60000). Emit HMBS_UPSTREAM_TEST_RESULT.
#
# We run both phases unconditionally: the consumer test is cheap and
# proves the package layout; the upstream test is the real gate. A
# failure in either phase is a failure of test_package.
set -eu

res_dir="${CONAN_PACKAGE_FOLDER_pako:-}/res/pako"

if [ -z "${CONAN_PACKAGE_FOLDER_pako:-}" ] || [ ! -d "$res_dir" ]; then
    echo "ERROR: CONAN_PACKAGE_FOLDER_pako not set or res/pako missing" >&2
    exit 1
fi

# ---- Phase 1: consumer test ------------------------------------------------
consumer_rc=0
consumer_out=$(node --jitless -e "
var pako = require('$res_dir');
var input = 'hello pako';
var compressed = pako.deflate(input);
var decompressed = pako.inflate(compressed, { to: 'string' });
process.stdout.write(decompressed);
" 2>&1) || consumer_rc=$?

if [ "$consumer_rc" -eq 0 ] && [ "$consumer_out" = "hello pako" ]; then
    consumer_passed=true
else
    consumer_passed=false
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"node --jitless -e (pako deflate/inflate round-trip)"}\n' "$consumer_passed"

if [ "$consumer_rc" -ne 0 ] || [ "$consumer_out" != "hello pako" ]; then
    echo "pako consumer test FAILED" >&2
    printf '%s\n' "$consumer_out" >&2
    exit 1
fi
echo "pako consumer test passed"

# ---- Phase 2: upstream mocha suite ----------------------------------------
# Copy the patched upstream source tree into a writable work directory
# so npm install can write node_modules/ there. The package folder is
# typically read-only.

upstream_discovered=150
upstream_status="failed"
upstream_executed=0
upstream_passed=0
upstream_failed=0
upstream_skipped=0

emit_marker() {
    printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"mocha","command":"node --jitless ./node_modules/.bin/_mocha -R spec -t 60000","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}\n' \
        "$upstream_status" "$upstream_discovered" "$upstream_executed" "$upstream_passed" "$upstream_failed" "$upstream_skipped"
}

# Writable work directory for npm install + mocha. Avoid mktemp -d on
# HMDFS (E112/E118: setgid 2700 Permission denied); fall back to a
# deterministic path under TMPDIR.
work_dir="${MOCHA_WORK_DIR:-${TMPDIR:-/tmp}/pako-mocha-$$}"
mkdir -p "$work_dir"

# Copy each upstream top-level entry individually. toybox cp handles
# explicit src args reliably, whereas `cp -r src/. dst/` is unevenly
# supported (hidden files, trailing-slash semantics). mocha resolves
# test/, index.js, lib/, package.json from the work_dir root.
for entry in test index.js lib package.json Makefile mocha.opts; do
    if [ -e "$res_dir/$entry" ]; then
        cp -r "$res_dir/$entry" "$work_dir/" 2>/dev/null || true
    fi
done
# Ensure test/ exists; if the copy failed we cannot run the suite.
if [ ! -d "$work_dir/test" ]; then
    echo "ERROR: upstream test/ tree missing from package" >&2
    emit_marker
    exit 1
fi

cd "$work_dir"

# Install devDependencies (mocha 1.21.5, lodash, async) with a China
# mirror for reliability. Failure here means we cannot run the upstream
# suite — report 0 executed and fail.
export npm_config_registry="${npm_config_registry:-https://registry.npmmirror.com}"
if ! command -v npm >/dev/null 2>&1; then
    echo "npm not available in PATH; cannot install mocha" >&2
    emit_marker
    exit 1
fi
if ! npm install --no-save --no-audit --no-fund mocha@1.21.5 lodash async >/dev/null 2>&1; then
    echo "npm install of upstream test dependencies failed" >&2
    emit_marker
    exit 1
fi

# node --jitless is required on OpenHarmony (V8 JIT exits with signal 5).
mocha_rc=0
mocha_out=$(node --jitless ./node_modules/.bin/_mocha -R spec -t 60000 2>&1) || mocha_rc=$?

# Surface the full mocha output so preflight logs are inspectable.
printf '%s\n' "$mocha_out"

# Parse mocha spec summary lines: "  N passing (duration)",
# "  N failing", "  N pending". Fall back to 0 when a line is absent.
upstream_passed=$(printf '%s\n' "$mocha_out" | grep -Eo '[0-9]+ passing' | grep -Eo '[0-9]+' | head -n1 || true)
upstream_failed=$(printf '%s\n' "$mocha_out"  | grep -Eo '[0-9]+ failing'  | grep -Eo '[0-9]+' | head -n1 || true)
upstream_skipped=$(printf '%s\n' "$mocha_out" | grep -Eo '[0-9]+ pending'  | grep -Eo '[0-9]+' | head -n1 || true)
upstream_passed=${upstream_passed:-0}
upstream_failed=${upstream_failed:-0}
upstream_skipped=${upstream_skipped:-0}
# executed = cases mocha actually ran (passing + failing). pending are
# discovered but not executed.
upstream_executed=$((upstream_passed + upstream_failed))

# Status is "passed" only when mocha exited 0 AND there were no failures.
if [ "$mocha_rc" -eq 0 ] && [ "$upstream_failed" -eq 0 ]; then
    upstream_status="passed"
fi

emit_marker

exit "$mocha_rc"
