#!/bin/sh
# test_cvsgraph.sh — manual verification of the installed cvsgraph binary.
# Mirrors test_package/conanfile.py: version smoke + real RCS→PNG render.
# Run from any writable directory (OHOS /tmp may be read-only).
# CVSGRAPH may point at the package bin (conanrun PATH does NOT include
# the tested package's own bin/ on this Conan build):
#   CVSGRAPH=<pkg>/bin/cvsgraph sh test_cvsgraph.sh
set -e

here=$(dirname "$0")
out="$PWD/cvsgraph-test-output.png"
CVSGRAPH="${CVSGRAPH:-cvsgraph}"

"$CVSGRAPH" -V
"$CVSGRAPH" -c "$here/cvsgraph.conf" -o "$out" -r "" "$here/test.txt,v"

# PNG magic check (portable: no xxd/od option differences)
if [ "$(head -c 4 "$out" | od -An -tx1 | tr -d ' \n')" != "89504e47" ]; then
    echo "FAIL: $out is not a PNG"
    exit 1
fi
echo "PASS: rendered $(wc -c < "$out") byte PNG from test.txt,v"
rm -f "$out"
