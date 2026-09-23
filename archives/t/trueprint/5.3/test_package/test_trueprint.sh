#!/bin/sh
# Consumer test for GNU trueprint 5.3 — asserts real formatting behaviour.
#
# trueprint "prints" by invoking the print command; TP_PRINT_CMD=cat routes
# the generated PostScript to stdout (same mechanism as the upstream test
# suite). TP_OPTS=--N (exported by the caller, mirroring tests/Run)
# suppresses the dated page headers so output stays deterministic.
set -e
BIN="$1"
SAMPLE="$2"
SPOOL="$3"
if [ -z "$BIN" ] || [ ! -x "$BIN/trueprint" ] || [ ! -f "$SAMPLE" ]; then
    echo "usage: test_trueprint.sh <package-bindir> <sample.c> <tmpdir>" >&2
    exit 2
fi
[ -n "$SPOOL" ] || { echo "usage: empty tmpdir argument" >&2; exit 2; }

# 1. version banner identifies the tool
"$BIN/trueprint" --version | grep -q "GNU Trueprint 5.3" || {
    echo "FAIL: unexpected --version output" >&2; exit 1; }

# 2. formatting a C file must produce PostScript on stdout
out=$(TP_PRINT_CMD=cat "$BIN/trueprint" "$SAMPLE")
echo "$out" | grep -q "%!PS-Adobe" || {
    echo "FAIL: no PostScript output for file input" >&2; exit 1; }

# 3. stdin input (spooled via TMPDIR thanks to the tmpfile fallback patch)
out=$(echo "int main(void){return 0;}" | \
      TMPDIR="$SPOOL" TP_PRINT_CMD=cat "$BIN/trueprint" -)
echo "$out" | grep -q "%!PS-Adobe" || {
    echo "FAIL: no PostScript output for stdin input" >&2; exit 1; }

# the stdin spool file is created by trueprint itself; clean it up
rm -f "$SPOOL"/trueprint??????

echo "trueprint 5.3 consumer test: OK (version/file-formatting/stdin assertions)"
