#!/usr/bin/env bash
# Run the complete upstream pako mocha test suite.
#
# pako's Makefile `test` target runs `mocha`. The mocha.opts file sets
# `-R spec -t 60000`. The test suite has 150 `it()` cases across
# deflate.js (40), inflate.js (38), inflate_cover_ported.js (47),
# strings.js (7), chunks.js (7), deflate_cover.js (6), gzip_specials.js
# (3), misc.js (2).
#
# The tests require devDependencies: mocha, lodash, async. We install
# these with npm (China mirror for reliability) before running mocha.
#
# After mocha finishes we emit the HMBS_UPSTREAM_TEST_RESULT JSON marker
# required by the hmbs preflight gate. The numbers come from mocha's own
# spec summary line (passing/failing/pending); discovered is the static
# count of `it()` across the test files, executed is passing+failing
# (mocha reports pending separately and does not run them).
set -euo pipefail

command -v node >/dev/null 2>&1 || {
    echo "pako requires a Node.js runtime in PATH" >&2
    exit 1
}

# Static count of upstream `it()` cases (the discovered suite size),
# verified by `grep -E '^\s*it\(' test/*.js` against the unpacked
# 08c5cfb archive:
#   deflate 40 + inflate 38 + inflate_cover_ported 47 + strings 7 +
#   chunks 7 + deflate_cover 6 + gzip_specials 3 + misc 2 = 150.
# mocha 1.21.5 reports 150 passing / 0 failing / 0 pending, matching
# the static count (deflate.js has 3 pairs of same-title `it()` —
# `level 0`, `level 1`, `level 4` — but each pair shares one body
# via a shared testSamples() call, so mocha counts them once each;
# the 40 static `it()` in deflate.js run as 40 mocha cases).
HMBS_DISCOVERED=150

# Install devDependencies needed by the mocha test runner.
# mocha 1.x is the version pinned in pako's package.json (1.21.5).
export npm_config_registry="${npm_config_registry:-https://registry.npmmirror.com}"
npm install --no-save --no-audit --no-fund mocha@1.21.5 lodash async 2>&1 || {
    echo "npm install of test dependencies failed" >&2
    exit 1
}

# Run the upstream mocha suite, capturing stdout+stderr to parse the
# spec summary. node --jitless is required on OpenHarmony (V8 JIT exits
# with signal 5).
MOCHA_OUT="$(node --jitless ./node_modules/.bin/_mocha -R spec -t 60000 2>&1)" || MOCHA_RC=$?
MOCHA_RC=${MOCHA_RC:-0}

# Surface the full mocha output so preflight logs are inspectable.
printf '%s\n' "$MOCHA_OUT"

# Parse mocha spec summary lines: "  N passing (duration)", "  N failing",
# "  N pending". Fall back to 0 when a line is absent.
HMBS_PASSED=$(printf '%s\n' "$MOCHA_OUT" | grep -Eo '[0-9]+ passing' | grep -Eo '[0-9]+' | head -n1 || true)
HMBS_FAILED=$(printf '%s\n' "$MOCHA_OUT"  | grep -Eo '[0-9]+ failing'  | grep -Eo '[0-9]+' | head -n1 || true)
HMBS_SKIPPED=$(printf '%s\n' "$MOCHA_OUT" | grep -Eo '[0-9]+ pending'  | grep -Eo '[0-9]+' | head -n1 || true)
HMBS_PASSED=${HMBS_PASSED:-0}
HMBS_FAILED=${HMBS_FAILED:-0}
HMBS_SKIPPED=${HMBS_SKIPPED:-0}
# executed = cases mocha actually ran (passing + failing). pending are
# discovered but not executed.
HMBS_EXECUTED=$((HMBS_PASSED + HMBS_FAILED))

# Emit the hmbs gate marker. Status is "passed" only when mocha exited 0
# AND there were no failures. JSON is single-line, keys in the order
# required by the hmbs contract.
if [ "$MOCHA_RC" -eq 0 ] && [ "$HMBS_FAILED" -eq 0 ]; then
    HMBS_STATUS="passed"
else
    HMBS_STATUS="failed"
fi

printf 'HMBS_UPSTREAM_TEST_RESULT={"status":"%s","framework":"mocha","command":"node --jitless ./node_modules/.bin/_mocha -R spec -t 60000","discovered":%d,"executed":%d,"passed":%d,"failed":%d,"skipped":%d}\n' \
    "$HMBS_STATUS" "$HMBS_DISCOVERED" "$HMBS_EXECUTED" "$HMBS_PASSED" "$HMBS_FAILED" "$HMBS_SKIPPED"

# Propagate mocha's exit code so conan create fails when tests fail.
exit "$MOCHA_RC"
