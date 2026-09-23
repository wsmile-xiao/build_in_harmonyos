#!/bin/sh
# test_package/test.sh -- paperjam 1.2.2 consumer functional test.
# Runs under the conanrun env. Every check invokes the real packaged binary;
# no check can pass without executing paperjam. Counts feed HMBS markers.
# POSIX sh only (HMBS shell_getcwd: run with injected SHELL=/bin/sh, never
# hardcode /data/service/hnp/bin/bash; no set -e/-u/pipefail: toybox ash
# rejects them under some builds).
# HMBS readonly_tmp: /tmp is read-only on device; all temp files live under
# TMPDIR/TMP/TEMP injected by conanfile (which points at the writable runtime
# tmp). mktemp always uses an explicit template under that dir.
# HMBS stale_runtime_library: device loader may ignore LD_LIBRARY_PATH, so
# the paperjam binary carries DT_RPATH to the conan dep lib dirs (see main
# recipe build()). LD_PRELOAD must stay unset: preloading libqpdf.so aborts
# on OHOS with `Error loading shared library libjpeg.so.62` before the
# binary even runs (2 consecutive preflights, both preload orders).
unset LD_PRELOAD

PASS=0
FAIL=0
DISCOVERED=6

BASE_TMP="${TMPDIR:-${TMP:-${TEMP:-}}}"
if [ -z "$BASE_TMP" ] || [ ! -d "$BASE_TMP" ]; then
    BASE_TMP="."
fi
WORKDIR="$(mktemp -d "${BASE_TMP}/paperjam.XXXXXX" 2>/dev/null)"
if [ -z "$WORKDIR" ] || [ ! -d "$WORKDIR" ]; then
    WORKDIR="${BASE_TMP}/paperjam.work.$$"
    mkdir -p "$WORKDIR" || exit 1
fi
trap 'rm -rf "$WORKDIR"' EXIT INT TERM
cd "$WORKDIR" || exit 1

PJ="${PAPERJAM_BIN:-paperjam}"

echo "[env] TMPDIR=${TMPDIR:-<unset>} BASE_TMP=$BASE_TMP WORKDIR=$WORKDIR"
echo "[env] LD_LIBRARY_PATH=${LD_LIBRARY_PATH:-<unset>}"
echo "[env] LD_PRELOAD=${LD_PRELOAD:-<unset>}"
if command -v ldd >/dev/null 2>&1; then
    echo "[ldd]"
    ldd "$PJ" 2>&1 || true
fi

report() {
    if [ "$2" -eq 0 ]; then
        PASS=$((PASS + 1))
        echo "[PASS] $1"
    else
        FAIL=$((FAIL + 1))
        echo "[FAIL] $1"
    fi
}

# Minimal one-page PDF generator (correct xref offsets via python3).
make_pdf() {
    python3 - "$1" <<'EOF'
import sys
path = sys.argv[1]
objs = [
    b"<< /Type /Catalog /Pages 2 0 R >>",
    b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
    b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] >>",
]
out = bytearray(b"%PDF-1.4\n")
offsets = []
for i, body in enumerate(objs, start=1):
    offsets.append(len(out))
    out += ("%d 0 obj\n" % i).encode() + body + b"\nendobj\n"
xref_pos = len(out)
out += ("xref\n0 %d\n" % (len(objs) + 1)).encode()
out += b"0000000000 65535 f \n"
for o in offsets:
    out += ("%010d 00000 n \n" % o).encode()
out += ("trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref_pos)).encode()
open(path, "wb").write(bytes(out))
EOF
}

# --- 1: --version reports PaperJam 1.2.2 -----------------------------------
out="$("$PJ" --version 2>&1)"
rc=$?
echo "$out" | grep -q "PaperJam 1.2.2"
report "paperjam --version reports 1.2.2 (output: ${out:-<empty>})" $((rc + $?))

# --- 2: --help prints usage --------------------------------------------------
out="$("$PJ" --help 2>&1)"
rc=$?
echo "$out" | grep -q "Usage: paperjam"
report "paperjam --help prints usage" $((rc + $?))

# --- fixture -----------------------------------------------------------------
make_pdf in.pdf
[ -s in.pdf ]
report "fixture in.pdf generated non-empty" $?

# --- 3: unknown paper name is rejected (vendored shim error path) -------------
out="$("$PJ" 'paper(paper=nosuchpaper99)' in.pdf bad.pdf 2>&1)"
rc=$?
echo "$out" | grep -qi "No paper"
grep_ok=$?
[ $rc -ne 0 ] && [ $grep_ok -eq 0 ]
report "unknown paper name rejected with 'No paper' (rc=$rc)" $?

# --- 4: null pipeline round-trips the PDF ------------------------------------
"$PJ" 'null' in.pdf out.pdf 2>null.log
rc=$?
[ $rc -eq 0 ] && [ -s out.pdf ] && head -c 4 out.pdf | grep -q "%PDF"
report "paperjam 'null' round-trips PDF to non-empty %PDF output (rc=$rc)" $?

# --- 5: named paper path uses shim table (a4) ---------------------------------
"$PJ" 'paper(paper=a4)' in.pdf out2.pdf 2>a4.log
rc=$?
[ $rc -eq 0 ] && [ -s out2.pdf ] && head -c 4 out2.pdf | grep -q "%PDF"
report "paperjam 'paper(paper=a4)' produces non-empty %PDF output (rc=$rc)" $?

# --- hmbs hard-gate marker (numbers come from the counters above) -------------
passed="true"
if [ "$PASS" -ne "$DISCOVERED" ] || [ "$FAIL" -ne 0 ]; then
    passed="false"
fi
printf 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":%s,"command":"bash test.sh","discovered":%d,"passedCount":%d}\n' \
    "$passed" "$DISCOVERED" "$PASS"

echo "=== test_package summary: ${PASS}/${DISCOVERED} passed, ${FAIL} failed ==="
echo "RESULT: $PASS passed, $FAIL failed"
if [ "$FAIL" -ne 0 ] || [ "$PASS" -ne "$DISCOVERED" ]; then
    exit 1
fi
exit 0
