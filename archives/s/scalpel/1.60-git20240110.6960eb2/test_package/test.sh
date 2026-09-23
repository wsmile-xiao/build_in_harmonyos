#!/bin/sh
# test_package consumer test for scalpel.
# Verifies a consumer can invoke the installed scalpel binary end to end:
# version banner + a real forensic carve (3 HTML blocks out of a raw image).
set -e

export PATH="$PATH:/system/bin"

SCALPEL=$(command -v scalpel)
[ -n "$SCALPEL" ] || { echo "FAIL: scalpel not found in PATH"; exit 1; }
BINDIR=$(dirname "$SCALPEL")
cd "$(pwd)"

echo "--- scalpel consumer verification ---"
echo "binary: $SCALPEL"

rm -rf carved_out image.img scalpel.conf carve_run.log

# build image: noise + <html>alpha</html> + gap + <html>beta</html> + noise
# + <html>gamma</html> + trailing noise
python3 - <<'EOF'
blocks = [b"<html>alpha</html>", b"<html>beta</html>", b"<html>gamma</html>"]
img = b"\x00" * 1024
img += blocks[0] + b"\x00" * 512 + blocks[1] + b"JUNKJUNK" * 40 + blocks[2] + b"\x00" * 2048
open("image.img", "wb").write(img)
# scalpel.conf is TAB-separated: <extension> <case-sensitive> <max-size> <header> <footer>
conf = "html\ty\t100000\t<html\t</html>\n"
open("scalpel.conf", "w").write(conf + "# seeded by test_package\n")
EOF

# 1. version banner (upstream usage()/banner exits 1 by design for -h; assert
#    on the observable banner text, not the exit code)
banner=$("$SCALPEL" -h 2>/dev/null || true)
echo "$banner" | grep -q "Scalpel version 1.60" || {
  echo "FAIL: banner does not contain 'Scalpel version 1.60'"; exit 1; }
echo "PASS 1: version banner -> $(echo "$banner" | head -1)"

# 2. end-to-end carve; scalpel refuses a pre-existing non-empty output dir
#    (forensic soundness), so carved_out must not exist yet
rc=0
"$SCALPEL" -c scalpel.conf -o carved_out image.img > carve_run.log 2>&1 || rc=$?
[ "$rc" = "0" ] || { echo "FAIL: scalpel carve exit=$rc"; cat carve_run.log; exit 1; }
echo "PASS 2: carve run exit=0"

# 3. carved exactly 3 .html files
n=$(find carved_out -name "*.html" -type f | wc -l)
[ "$n" = "3" ] || { echo "FAIL: expected 3 carved files, got $n"; find carved_out -type f; exit 1; }
echo "PASS 3: carved file count = 3"

# 4-6. carved content byte-exact (alpha / beta / gamma)
for word in alpha beta gamma; do
  grep -rq "<html>${word}</html>" carved_out || {
    echo "FAIL: block <html>${word}</html> not carved"; exit 1; }
  echo "PASS: carved content contains <html>${word}</html>"
done

# 7. audit log records the carve (upstream writes a per-file listing and a
#    "Completed at" line into audit.txt; the "files carved = N" total goes to
#    stdout only)
[ -f carved_out/audit.txt ] || { echo "FAIL: audit.txt missing"; exit 1; }
grep -q "The following files were carved:" carved_out/audit.txt || {
  echo "FAIL: audit.txt missing carved-file listing"; exit 1; }
n_audit=$(grep -c "\.html" carved_out/audit.txt)
[ "$n_audit" = "3" ] || { echo "FAIL: audit.txt lists $n_audit carved html rows, want 3"; exit 1; }
grep -q "Completed at" carved_out/audit.txt || {
  echo "FAIL: audit.txt missing completion line"; exit 1; }
echo "PASS 7: audit.txt lists 3 carved files and completion line"

# 8. default config shipped next to the binary
[ -f "$BINDIR/scalpel.conf" ] || { echo "FAIL: default scalpel.conf missing beside binary"; exit 1; }
echo "PASS 8: default scalpel.conf shipped beside binary"

echo "test scalpel 1.60-git20240110.6960eb2: 8/8 checks PASS"
exit 0
