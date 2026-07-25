#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for man2html executable
# Runs in conanrun env (PATH includes installed bin/).
# R34: exercises the actual man2html binary by converting a man page to HTML.
#
# man2html 3.0.1 reads formatted nroff from STDIN only (no file args).
# See `Usage: $PROG [ options ] < infile > outfile` in source.
#
# test_package/conanfile.py passes the absolute path via MAN2HTML_BIN so we
# do not depend on PATH resolution.
set -euo pipefail

M2H="${MAN2HTML_BIN:-man2html}"

TMPDIR=$(mktemp -d 2>/dev/null || mktemp -d -t man2html_test)
trap 'rm -rf "$TMPDIR"' EXIT
MAN_INPUT="$TMPDIR/test.1"
HTML_OUT="$TMPDIR/test.html"

# Minimal pre-formatted man page content (what `man` would output to stdout)
cat > "$MAN_INPUT" <<'EOF'
TEST(1)                       User Commands                      TEST(1)

NAME
       test - a sample man page for testing

SYNOPSIS
       test [options]

DESCRIPTION
       This is a sample man page used to verify man2html converts to HTML.

SEE ALSO
       man(1)

TEST 1.0                        2026-07-13                        TEST(1)
EOF

# --- Environment diagnostics (always visible, helps debug) ---
echo "[diag] MAN2HTML_BIN=$M2H"
echo "[diag] man2html exists check:"
if [ -f "$M2H" ]; then
    echo "[diag] man2html file exists"
    echo "[diag] man2html shebang (first line):"
    head -1 "$M2H"
    echo "[diag] man2html file type:"
    ls -l "$M2H"
else
    echo "[diag] man2html file NOT FOUND at: $M2H"
    echo "[diag] listing parent directory:"
    ls -la "$(dirname "$M2H")" 2>&1 || echo "[diag] cannot list parent dir"
    exit 1
fi

echo "[diag] perl version:"
perl -v 2>&1

echo "[diag] checking Getopt::Long module:"
perl -e "use Getopt::Long; print qq([ok] Getopt::Long available\n)" 2>&1 || echo "[diag] Getopt::Long NOT available"

# --- Run man2html (stdin mode only — man2html does NOT support file args) ---
echo "[test] man2html conversion (stdin -> HTML)"
# Do NOT suppress stderr — we need to see any perl errors.
# Temporarily disable -e so we can capture the exit code and show diagnostics.
set +e
"$M2H" < "$MAN_INPUT" > "$HTML_OUT" 2>&1
RC=$?
set -e
echo "[diag] man2html exit code: $RC"

if [ $RC -ne 0 ]; then
    echo "[fail] man2html exited with code $RC"
    echo "[diag] full output (stdout+stderr):"
    cat "$HTML_OUT"
    exit 1
fi

echo "[ok] man2html ran successfully"

# Verify the output contains the HTML root element (case-insensitive)
if grep -iq '<html>' "$HTML_OUT"; then
    echo "[ok] HTML output detected"
    echo "[test] output snippet (first 5 lines):"
    head -5 "$HTML_OUT"
else
    echo "[fail] man2html produced non-HTML output"
    echo "[test] actual output (first 10 lines):"
    head -10 "$HTML_OUT"
    exit 1
fi

echo "[ok] all tests passed"
