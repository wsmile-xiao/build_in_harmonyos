#!/usr/bin/env bash
#
# test_xmlformat.sh — Conan L1 smoke test for xmlformat 1.04
#
# Verifies that:
#   1. xmlformat is installed and executable
#   2. Running it on a sample XML document produces formatted output
#      containing a properly indented child element (proves the core
#      API of the package is exercised, not just a version string).
#
# This is a real test (R34: substantively calls the packaged binary).
set -euo pipefail

XMLFORMAT="${1:-xmlformat}"

echo "=== test_xmlformat: checking $XMLFORMAT exists and is executable ==="
if ! command -v "$XMLFORMAT" >/dev/null 2>&1; then
    echo "FAIL: $XMLFORMAT not found in PATH"
    exit 1
fi

# Feed a tiny un-indented XML document to xmlformat and inspect the output.
# xmlformat normalises whitespace: the <child> text should end up on its
# own indented line (one leading space, since the parent <root> is at
# indent depth 0 and child elements gain one level).
INPUT='<root><child>value</child></root>'

echo "=== test_xmlformat: running $XMLFORMAT on sample XML ==="
OUTPUT=$(printf '%s' "$INPUT" | "$XMLFORMAT" 2>&1) || {
    rc=$?
    echo "FAIL: $XMLFORMAT returned exit code $rc"
    echo "Output: $OUTPUT"
    exit $rc
}

echo "Output:"
printf '%s\n' "$OUTPUT"

echo "=== test_xmlformat: checking formatted output ==="
# Expect the child element to appear indented on its own line:
#   <root>
#    <child>value</child>
#   </root>
if printf '%s\n' "$OUTPUT" | grep -Eq '^ <child>value</child>$'; then
    echo "PASS: formatted child element found on its own indented line"
else
    echo "FAIL: expected indented '<child>value</child>' line not found"
    echo "Got:"
    printf '%s\n' "$OUTPUT"
    exit 1
fi

echo "=== test_xmlformat: all checks passed ==="
exit 0
