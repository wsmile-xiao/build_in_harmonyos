#!/usr/bin/env bash
# R34: real smoke test for djvu2pdf 1.0 — exercises the packaged artifact.
# djvu2pdf is a bash script and djvu2pdf_toc_parser.py is a Python script.
# We verify presence, executable bit, shebang, syntax checks, and actual execution.
set -euo pipefail

BIN_DIR="${1:?usage: test_djvu2pdf.sh <package bin dir>}"

FAIL=0

# Check djvu2pdf shell script
DJVU2PDF="$BIN_DIR/djvu2pdf"
if [ ! -x "$DJVU2PDF" ]; then
    echo "        [fail] djvu2pdf missing or not executable in $BIN_DIR"
    FAIL=1
else
    SHEBANG=$(head -1 "$DJVU2PDF")
    if [[ "$SHEBANG" != *bash* ]]; then
        echo "        [fail] unexpected shebang for djvu2pdf: $SHEBANG"
        FAIL=1
    fi
    if ! bash -n "$DJVU2PDF"; then
        echo "        [fail] djvu2pdf bash syntax check failed"
        FAIL=1
    fi
    # R34: actual execution — running with no args should exit non-zero
    # (script expects exactly 2 arguments: input and output file)
    if "$DJVU2PDF" 2>/dev/null; then
        echo "        [fail] djvu2pdf should fail with no arguments"
        FAIL=1
    else
        echo "        [ok] djvu2pdf exits non-zero with no arguments (expected)"
    fi
fi

# Check djvu2pdf_toc_parser.py Python script
TOC_PARSER="$BIN_DIR/djvu2pdf_toc_parser.py"
if [ ! -f "$TOC_PARSER" ]; then
    echo "        [fail] djvu2pdf_toc_parser.py missing in $BIN_DIR"
    FAIL=1
else
    if ! python3 -c "import py_compile; py_compile.compile('$TOC_PARSER', doraise=True)"; then
        echo "        [fail] djvu2pdf_toc_parser.py Python syntax check failed"
        FAIL=1
    fi
    # R34: actual execution — running with empty stdin should produce no output
    if ! echo -n "" | python3 "$TOC_PARSER" 2>/dev/null; then
        echo "        [fail] djvu2pdf_toc_parser.py failed with empty stdin"
        FAIL=1
    else
        echo "        [ok] djvu2pdf_toc_parser.py handles empty input correctly"
    fi
fi

if [ "$FAIL" -eq 0 ]; then
    echo "        [ok] djvu2pdf smoke test: OK"
fi
exit "$FAIL"
