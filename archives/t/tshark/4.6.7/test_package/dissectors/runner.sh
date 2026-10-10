#!/usr/bin/env bash
# L2 test for tshark: 27 snapshot cases ported from the upstream wireshark
# pytest suite `test/suite_dissectors` (23 test functions; 27 collected items
# including the 7 zabbix parametrized sub-cases; asterix category 034 is
# disabled upstream via the `_disabled_` class-name prefix and is not run).
#
# Each case re-executes the exact upstream tshark command line against the
# exact upstream input capture and diffs the output against a snapshot
# captured from a verified-passing run on HarmonyOS (see data/cases.tsv for
# the upstream test mapping and data/<case>.meta per case).
#
# The upstream tests are pytest-based (pip pytest is unavailable in the CI
# clean environment), so they are ported to this output-snapshot form: every
# upstream assertion is a pure check on exactly these command outputs, so
# snapshot equivalence from a passing run preserves the assertions.
#
# Pure bash + tshark — no python/pytest needed at CI test time.
set -u

# tshark formats absolute (geninfo) times in the local timezone; pin UTC so
# the output is machine-independent (snapshots were captured with TZ=UTC).
export TZ=UTC

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DATA="$SCRIPT_DIR/data"

# PDML output embeds run-dependent values: the root <pdml> `time` attribute
# (wall clock), `capture_file` (absolute input path) and the doc-comment
# install path. Normalize them on both sides before diffing; every other
# byte must match exactly (that is where the dissector assertions live).
norm() {
    sed -E \
        -e '/^<pdml /{s/time="[^"]*"/time="X"/; s/capture_file="[^"]*"/capture_file="X"/}' \
        -e 's|in /[^ ]* or at|in X or at|' "$1" > "$2"
}

# Scratch dir: honor TMPDIR when writable, else fall back to $HOME/tmp
# (OHOS: /tmp is read-only, knowledge E002).
TMPD="${TMPDIR:-}"
if [ -z "$TMPD" ] || [ ! -w "$TMPD" ]; then
    TMPD="$HOME/tmp"
fi
mkdir -p "$TMPD"
TMP="$TMPD/tshark-l2-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

total=0
pass=0
fail=0

for argsfile in "$DATA"/case_*.args; do
    id="$(basename "$argsfile" .args)"
    input="$(cat "$DATA/$id.input")"
    # Captures are stored as <name>.b64: the GitCode PR .diff endpoint does not
    # carry binary payloads, so raw binaries cannot survive CI checkout
    # (git apply: "missing binary patch data"). Decode into the scratch dir.
    capture="$DATA/$input"
    if [ -f "$DATA/$input.b64" ]; then
        base64 -d "$DATA/$input.b64" > "$TMP/$input"
        capture="$TMP/$input"
    fi
    args=()
    while IFS= read -r line; do
        args+=("$line")
    done < "$argsfile"
    total=$((total + 1))
    upstream="$(cat "$DATA/$id.meta" 2>/dev/null || echo "$id")"
    if tshark -r "$capture" ${args[@]+"${args[@]}"} > "$TMP/$id.actual" 2> "$TMP/$id.err"; then
        norm "$DATA/$id.expected" "$TMP/$id.exp.norm"
        norm "$TMP/$id.actual" "$TMP/$id.act.norm"
        if diff -u "$TMP/$id.exp.norm" "$TMP/$id.act.norm" > "$TMP/$id.diff" 2>&1; then
            pass=$((pass + 1))
            echo "PASS  $id  $upstream"
        else
            fail=$((fail + 1))
            echo "FAIL  $id  $upstream  (output mismatch; first diff lines:)"
            head -10 "$TMP/$id.diff"
        fi
    else
        fail=$((fail + 1))
        echo "FAIL  $id  $upstream  (tshark exited nonzero; stderr:)"
        head -5 "$TMP/$id.err"
    fi
done

echo "L2 dissectors: $pass/$total passed, $fail failed"
[ "$fail" -eq 0 ]
