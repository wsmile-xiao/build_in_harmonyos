#!/data/service/hnp/bin/bash
# test_package/test.sh — substantive test for the podiff executable (R34).
# Runs in conanrun env; the packaged podiff binary path is passed as $1.
# Exit-code semantics asserted (verified against upstream 1.4 sources):
#   0 = identical translations, 1 = differing translations,
#   2 = invalid command line (man page RETURN VALUE),
#   3 = PO syntax error (podiff.l: if (yyparse()) exit(3);)
set -eu

PODIFF="${1:?usage: test.sh <path-to-podiff>}"
# L1e: package without the binary must fail here
if [ ! -x "$PODIFF" ]; then
    echo "FAIL: podiff binary missing or not executable: $PODIFF"
    exit 1
fi

# OHOS: /tmp is read-only (E002); podiff (patched) honors TMPDIR for its
# normalized temp files (mkstemp), so point it at a writable dir.
TMPD="$PWD/podiff-test-tmp"
rm -rf "$TMPD"
mkdir -p "$TMPD"
export TMPDIR="$TMPD"

# ── fixtures: two PO files with one identical pair and one differing pair ──
cat > a.po <<'EOF'
msgid ""
msgstr "Content-Type: text/plain; charset=UTF-8\n"

msgid "hello"
msgstr "你好"

msgid "world"
msgstr "世界"
EOF
cp a.po b.po                      # identical file           => exit 0
sed 's/世界/世上/' b.po > c.po     # differing translation    => exit 1
cat > bad.po <<'EOF'
this is not a valid PO file
EOF

echo "[test 1] podiff --version (exit 0)"
"$PODIFF" --version | head -1
"$PODIFF" --version | grep -q "podiff 1.4"
echo "OK: --version => podiff 1.4"

echo "[test 2] identical translations => exit 0"
"$PODIFF" a.po b.po
echo "OK: identical files => rc=0"

echo "[test 3] differing translation => exit 1 with diff output"
rc=0
OUT="$("$PODIFF" a.po c.po)" || rc=$?
[ "$rc" -eq 1 ] || { echo "FAIL: expected exit 1 (files differ), got $rc"; exit 1; }
echo "$OUT" | grep -q "msgstr" || { echo "FAIL: no diff output"; exit 1; }
echo "OK: differing translation => rc=1, diff output present"

echo "[test 4] PO syntax error => exit 3"
rc=0
"$PODIFF" a.po bad.po >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 3 ] || { echo "FAIL: expected exit 3 (PO syntax error), got $rc"; exit 1; }
echo "OK: invalid PO => rc=3"

echo "[test 5] invalid command line option => exit 2"
rc=0
"$PODIFF" -Z a.po b.po >/dev/null 2>&1 || rc=$?
[ "$rc" -eq 2 ] || { echo "FAIL: expected exit 2 (invalid option), got $rc"; exit 1; }
echo "OK: invalid option => rc=2"

echo "ALL PODIFF TESTS PASSED"
