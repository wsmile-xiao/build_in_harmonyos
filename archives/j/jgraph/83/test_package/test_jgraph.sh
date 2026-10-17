#!/usr/bin/env bash
# test_jgraph.sh — consumer tests for the packaged jgraph binary (R34).
#
# Drives the installed CLI and asserts observable behaviour:
#   1) PostScript rendering of a minimal graph (-P), deterministic output
#   2) -p show mode reproduces the parsed description
#   3) -L landscape page translation is numerically correct (int->double fix)
#   4) EPS mark bounding-box parsing, including the truncated-box error path
#   5) multi-page (newpage) output and -comments output
#   6) error handling for malformed input
#   7) the packaged artifact is an AArch64 ELF
#
# Upstream ships no test suite (see MANIFEST.yml); this suite is the
# adaptation's consumer coverage.

set -euo pipefail

if ! JGRAPH_BIN="$(command -v jgraph)"; then
    echo "        [fail] jgraph not found in PATH"
    exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
WORK_DIR="$(pwd)/jgraph-test.$$"
mkdir -p "$WORK_DIR"
# jgraph resolves EPS mark files relative to its working directory, so run
# from the temp dir with a copy of the inputs next to us.
cp "$SCRIPT_DIR"/inputs/*.jgr "$SCRIPT_DIR"/inputs/*.eps "$WORK_DIR/"
cd "$WORK_DIR"
trap 'rm -rf "$WORK_DIR"' EXIT

PASS_COUNT=0
FAIL_COUNT=0
pass() { PASS_COUNT=$((PASS_COUNT + 1)); echo "        [ok] $1"; }
fail() { FAIL_COUNT=$((FAIL_COUNT + 1)); echo "        [fail] $1"; }
assert_eq() {  # desc expected actual
    if [ "$3" = "$2" ]; then
        pass "$1 (=$3)"
    else
        fail "$1 (expected $2, got $3)"
    fi
}
assert_contains() {  # desc haystack needle
    case "$2" in
        *"$3"*) pass "$1" ;;
        *) fail "$1 (missing: $3)" ;;
    esac
}

echo "[step] jgraph consumer tests"

if [ -x "$JGRAPH_BIN" ]; then
    pass "binary installed and executable"
else
    fail "binary installed and executable"
fi

# ── 1. render + determinism ─────────────────────────────────────────────────
RC=0
"$JGRAPH_BIN" -P < "$SCRIPT_DIR/inputs/simple.jgr" > simple.ps 2> simple.err || RC=$?
assert_eq "minimal graph renders (rc)" 0 "$RC"
SIMPLE_PS="$(cat simple.ps)"
assert_contains "PostScript header emitted" "$SIMPLE_PS" "%!PS-Adobe-2.0 EPSF-1.2"
assert_contains "bounding box computed" "$SIMPLE_PS" "%%BoundingBox: -27 -45 219 219"
assert_contains "font selected" "$SIMPLE_PS" "/Times-Roman findfont"

"$JGRAPH_BIN" -P < "$SCRIPT_DIR/inputs/simple.jgr" > simple2.ps
HASH_1="$(sha256sum simple.ps | awk '{print $1}')"
HASH_2="$(sha256sum simple2.ps | awk '{print $1}')"
assert_eq "rendering is deterministic" "$HASH_1" "$HASH_2"

# ── 2. -p show mode ─────────────────────────────────────────────────────────
RC=0
"$JGRAPH_BIN" -p < "$SCRIPT_DIR/inputs/simple.jgr" > simple.show 2> show.err || RC=$?
assert_eq "-p show mode (rc)" 0 "$RC"
SHOW="$(cat simple.show)"
assert_contains "show: graph block" "$SHOW" "graph 0"
assert_contains "show: xaxis block" "$SHOW" "xaxis"
assert_contains "show: title text" "$SHOW" "Simple"
assert_contains "show: curve block" "$SHOW" "curve 0"

# ── 3. landscape translate (int -> double fix) ──────────────────────────────
# In the landscape BoundingBox line the fields are bb[1] bb[0] bb[3] bb[2]
# and the page translate that follows must be exactly -bb[2]-bb[0].
RC=0
"$JGRAPH_BIN" -L < "$SCRIPT_DIR/inputs/simple.jgr" > landscape.ps 2> landscape.err || RC=$?
assert_eq "landscape render (rc)" 0 "$RC"
BBOX_LINE="$(grep -m1 '^%%BoundingBox:' landscape.ps)"
assert_contains "landscape bounding box order" "$BBOX_LINE" "-45 -27 219 219"
set -- $BBOX_LINE
EXPECTED="$(awk -v bb2="$5" -v bb0="$3" 'BEGIN { printf "%.6f", -bb2 - bb0 }')"
TRANSLATE_LINE="$(grep -m1 ' 0 translate' landscape.ps)"
ACTUAL="${TRANSLATE_LINE%% *}"
assert_eq "landscape translate equals -bb[2]-bb[0]" "$EXPECTED" "$ACTUAL"

# ── 4. EPS mark bounding box ────────────────────────────────────────────────
RC=0
"$JGRAPH_BIN" -P < "$SCRIPT_DIR/inputs/eps-good.jgr" > eps-good.ps 2> eps-good.err || RC=$?
assert_eq "EPS mark renders (rc)" 0 "$RC"
if [ -s eps-good.ps ]; then
    pass "EPS mark output is non-empty"
else
    fail "EPS mark output is non-empty"
fi

RC=0
EPS_ERR="$("$JGRAPH_BIN" -P < "$SCRIPT_DIR/inputs/eps-bad.jgr" 2>&1 >/dev/null)" || RC=$?
assert_eq "truncated EPS BoundingBox rejected (rc)" 1 "$RC"
assert_contains "truncated EPS diagnostic" "$EPS_ERR" "eof in bounding box"

# ── 5. multi-page and -comments output ──────────────────────────────────────
RC=0
"$JGRAPH_BIN" -P < "$SCRIPT_DIR/inputs/twopage.jgr" > twopage.ps 2> twopage.err || RC=$?
assert_eq "multi-page render (rc)" 0 "$RC"
TWOPAGE_PS="$(cat twopage.ps)"
assert_contains "page 1 emitted" "$TWOPAGE_PS" "%%Page: 1 1"
assert_contains "page 2 emitted" "$TWOPAGE_PS" "%%Page: 2 2"

COMMENT_COUNT="$("$JGRAPH_BIN" -comments -P < "$SCRIPT_DIR/inputs/simple.jgr" | grep -c '^% ')"
if [ "$COMMENT_COUNT" -ge 10 ]; then
    pass "-comments emits PostScript comments ($COMMENT_COUNT lines)"
else
    fail "-comments emits PostScript comments (got $COMMENT_COUNT lines)"
fi

# ── 6. malformed input ──────────────────────────────────────────────────────
RC=0
BAD_ERR="$(printf 'bogus_keyword\n' | "$JGRAPH_BIN" -P 2>&1 >/dev/null)" || RC=$?
assert_eq "malformed input rejected (rc)" 1 "$RC"
assert_contains "malformed input diagnostic" "$BAD_ERR" "Bad token: bogus_keyword"

# ── 7. artifact sanity ──────────────────────────────────────────────────────
if python3 - "$JGRAPH_BIN" <<'PY'
import struct
import sys

with open(sys.argv[1], "rb") as fh:
    header = fh.read(20)
if header[:4] != b"\x7fELF":
    raise SystemExit("not an ELF file")
if struct.unpack_from("<H", header, 18)[0] != 183:
    raise SystemExit("not AArch64")
PY
then
    pass "packaged artifact is an AArch64 ELF"
else
    fail "packaged artifact is an AArch64 ELF"
fi

echo "[step] jgraph consumer tests: $PASS_COUNT passed, $FAIL_COUNT failed"
if [ "$FAIL_COUNT" -ne 0 ]; then
    echo "[fail] $FAIL_COUNT assertion(s) failed"
    exit 1
fi
echo "[ok] all $PASS_COUNT assertions passed"
