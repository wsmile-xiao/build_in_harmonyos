#!/data/service/hnp/bin/bash
# Consumer test for the installed liblcf-tools binaries.
set -euo pipefail

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

TEST_ROOT="${TMPDIR:-$HOME/tmp}/liblcf-tools-test-$$"
mkdir -p "$TEST_ROOT"
trap 'rm -rf "$TEST_ROOT"' EXIT

command -v lcfstrings >/dev/null 2>&1 || fail "lcfstrings is not on PATH"
command -v lcf2xml >/dev/null 2>&1 || fail "lcf2xml is not on PATH"

set +e
STRINGS_HELP=$(lcfstrings --help 2>&1)
STRINGS_HELP_RC=$?
set -e
[ "$STRINGS_HELP_RC" -eq 2 ] || fail "lcfstrings --help returned $STRINGS_HELP_RC, expected 2"
echo "$STRINGS_HELP" | grep -q "Extract all strings" || fail "lcfstrings help text missing"

set +e
LCF2XML_HELP=$(lcf2xml 2>&1)
LCF2XML_HELP_RC=$?
set -e
[ "$LCF2XML_HELP_RC" -eq 1 ] || fail "lcf2xml without input returned $LCF2XML_HELP_RC, expected 1"
echo "$LCF2XML_HELP" | grep -q "LCF2XML" || fail "lcf2xml usage text missing"

# An empty LMT is a valid deterministic XML document. Round-trip it through
# both directions to exercise the installed parser/writer rather than only
# checking --help output.
cat > "$TEST_ROOT/sample.xml" <<'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<LMT>
</LMT>
EOF

(
    cd "$TEST_ROOT"
    lcf2xml sample.xml
)
[ -s "$TEST_ROOT/sample.lmt" ] || fail "lcf2xml did not create sample.lmt"

(
    cd "$TEST_ROOT"
    lcfstrings sample.lmt > strings.txt
    lcf2xml sample.lmt
)
[ -s "$TEST_ROOT/sample.emt" ] || fail "lcf2xml did not create sample.emt"
grep -q "<LMT" "$TEST_ROOT/sample.emt" || fail "round-trip XML does not contain LMT root"

# lcfstrings successfully consumed the generated LMT; an empty string list is
# expected for the empty fixture.
[ -f "$TEST_ROOT/strings.txt" ] || fail "lcfstrings did not create output"

echo "ALL TESTS PASSED"
