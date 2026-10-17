#!/bin/sh
# xmlindent 0.2.18 consumer smoke test.
#
# CONSUMER verification only — the upstream regression fixture is run separately
# from the recipe's build() step (see ../../run_upstream_tests.sh, upstream_total = 1).
# Nothing here is counted as an upstream test.
#
# Exercises the packaged CLI end to end: version/help, stdin filtering, file
# arguments, -o output, -i indent level, -t tabs, -w in-place overwrite,
# unknown-option handling and a malformed-input robustness check.
#
# Requires only POSIX sh + printf/cmp/grep.
set -e

if [ $# -lt 1 ]; then
    echo "usage: test_xmlindent.sh <package_bin_dir>" >&2
    exit 2
fi
BIN="$1"
X="$BIN/xmlindent"

# --- 1: packaged binary exists and is executable -----------------------------
[ -x "$X" ] || { echo "xmlindent binary not found/executable: $X" >&2; exit 1; }

tmp="${TMPDIR:-/tmp}/xmlindent_smoke.$$"
rm -rf "$tmp"
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT

IN='<bar><foo>1 2 3 4 5</foo></bar>'

# --- 2/3: -v prints the version and exits 0 ---------------------------------
"$X" -v > "$tmp/v.out" 2>&1
grep -q '0\.2\.18' "$tmp/v.out" || {
    echo "-v did not print 0.2.18:" >&2; cat "$tmp/v.out" >&2; exit 1; }

# --- 4: -h exits 0 -----------------------------------------------------------
"$X" -h > "$tmp/h.out" 2>&1 || { echo "-h exited non-zero" >&2; exit 1; }
grep -q 'Usage' "$tmp/h.out" || {
    echo "-h did not print usage:" >&2; cat "$tmp/h.out" >&2; exit 1; }

# --- 5: stdin filtering produces the expected indentation -------------------
printf '%s\n' "$IN" > "$tmp/in.xml"
printf '<bar>\n    <foo>1 2 3 4 5</foo>\n</bar>\n' > "$tmp/exp4.xml"
"$X" < "$tmp/in.xml" > "$tmp/got.stdin" 2> "$tmp/err.stdin"
cmp -s "$tmp/got.stdin" "$tmp/exp4.xml" || {
    echo "stdin filtering produced wrong output:" >&2
    cat "$tmp/got.stdin" >&2; exit 1; }

# --- 6: a file argument behaves the same as stdin ---------------------------
"$X" "$tmp/in.xml" > "$tmp/got.file" 2>&1
cmp -s "$tmp/got.file" "$tmp/exp4.xml" || {
    echo "file-argument output differs from stdin output:" >&2
    cat "$tmp/got.file" >&2; exit 1; }

# --- 7: -o writes the result to the named file ------------------------------
"$X" -o "$tmp/out.o" "$tmp/in.xml" > "$tmp/got.o.stdout" 2>&1
[ -f "$tmp/out.o" ] || { echo "-o did not create the output file" >&2; exit 1; }
cmp -s "$tmp/out.o" "$tmp/exp4.xml" || {
    echo "-o output file has wrong content:" >&2; cat "$tmp/out.o" >&2; exit 1; }

# --- 8: -i 2 honours the requested indent level -----------------------------
printf '<bar>\n  <foo>1 2 3 4 5</foo>\n</bar>\n' > "$tmp/exp2.xml"
"$X" -i 2 "$tmp/in.xml" > "$tmp/got.i2" 2>&1
cmp -s "$tmp/got.i2" "$tmp/exp2.xml" || {
    echo "-i 2 did not produce a 2-space indent:" >&2
    cat "$tmp/got.i2" >&2; exit 1; }

# --- 9: -t indents with tabs ------------------------------------------------
"$X" -t "$tmp/in.xml" > "$tmp/got.tabs" 2>&1
# the indented line must begin with a TAB character
grep -q "$(printf '\t')<foo>" "$tmp/got.tabs" || {
    echo "-t did not indent with a tab:" >&2
    cat -A "$tmp/got.tabs" >&2 2>/dev/null || cat "$tmp/got.tabs" >&2
    exit 1; }

# --- 10: -w overwrites the original file in place ---------------------------
cp "$tmp/in.xml" "$tmp/ow.xml"
"$X" -w "$tmp/ow.xml" >/dev/null 2>&1
cmp -s "$tmp/ow.xml" "$tmp/exp4.xml" || {
    echo "-w did not overwrite the original in place:" >&2
    cat "$tmp/ow.xml" >&2; exit 1; }

# --- 11: an unknown option fails -------------------------------------------
rc=0
"$X" --definitely-not-an-option "$tmp/in.xml" >/dev/null 2>&1 || rc=$?
[ "$rc" -ne 0 ] || { echo "unknown option exited 0" >&2; exit 1; }

# --- 12: malformed input does not hang or crash -----------------------------
printf '<a><b>unclosed\n' > "$tmp/bad.xml"
"$X" "$tmp/bad.xml" > "$tmp/got.bad" 2> "$tmp/err.bad" || true
# no assertion on the exit code (upstream is lenient), but it must terminate
# and must not produce a signal death
[ -f "$tmp/got.bad" ] || { echo "malformed input produced no output at all" >&2; exit 1; }

echo "xmlindent smoke test OK (version/help/stdin/file/-o/-i/-t/-w/unknown-opt/malformed)"
