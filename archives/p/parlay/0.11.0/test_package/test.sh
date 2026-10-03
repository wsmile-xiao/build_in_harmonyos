#!/bin/sh
# test_package/test.sh — consumer smoke test for parlay executable
# Asserts: (1) --version reports 0.11.0; (2) --help lists ecosystems/snyk/scorecard;
#          (3) missing-file enrich path fails closed; (4) top-level help mentions SBOM.
set -eu

# HMBS injects TMPDIR/TMP/TEMP; cd there so the shell is not left in an HMDFS
# cwd that breaks getcwd.
cd "${TMPDIR:-${TMP:-${TEMP:-/tmp}}}" 2>/dev/null || cd /tmp 2>/dev/null || true

if [ "$#" -ne 1 ]; then
    echo "usage: $0 <path-to-parlay>" >&2
    exit 2
fi

parlay_bin="$1"

if [ ! -f "$parlay_bin" ]; then
    echo "parlay binary not found: $parlay_bin" >&2
    exit 1
fi

echo "[test 1] parlay --version reports 0.11.0"
version_output="$("$parlay_bin" --version 2>&1)"
echo "version output: $version_output"
printf '%s\n' "$version_output" | grep -F "0.11.0" >/dev/null
echo "        [ok] version check passed"

echo "[test 2] parlay --help lists core subcommands"
help_output="$("$parlay_bin" --help 2>&1)"
echo "$help_output" | grep -F "ecosystems" >/dev/null
echo "$help_output" | grep -F "snyk" >/dev/null
echo "$help_output" | grep -F "scorecard" >/dev/null
echo "        [ok] help subcommands check passed"

echo "[test 3] parlay ecosystems enrich not-here fails closed"
neg_tmpdir="${TMPDIR:-${TMP:-${TEMP:-/tmp}}}"
mkdir -p "$neg_tmpdir" 2>/dev/null || true
neg_out="$neg_tmpdir/parlay-neg-$$.out"
set +e
"$parlay_bin" ecosystems enrich not-here > "$neg_out" 2>&1
neg_rc=$?
set -e
echo "negative exit code: $neg_rc"
cat "$neg_out" || true
rm -f "$neg_out"
[ "$neg_rc" -ne 0 ]
echo "        [ok] negative path check passed"

echo "[test 4] parlay --help mentions SBOM"
printf '%s\n' "$help_output" | grep -qi "SBOM" >/dev/null
echo "        [ok] SBOM mention check passed"

echo "[ok] All 4 tests passed."
