#!/bin/sh
# test_package consumer test for sgml 0.6.3 (sgml-common).
# Exercises the installed tools end-to-end and validates the installed data tree.
set -e
: "${TMPDIR:=/tmp}"
mkdir -p "$TMPDIR"

echo "--- sgml 0.6.3 consumer verification ---"

# Locate installed tree from the tool on PATH (VirtualRunEnv injects package bin)
bindir=$(dirname "$(command -v sgmlwhich)")
prefix=$(cd "$bindir/.." && pwd)
sgmldir="$prefix/share/sgml"

# 1. sgmlwhich prints the expected sgml.conf location
out1=$(sgmlwhich)
[ "$out1" = "/etc/sgml/sgml.conf" ] || { echo "FAIL: sgmlwhich -> [$out1]"; exit 1; }
echo "PASS 1: sgmlwhich -> $out1"

# 2. install-catalog --version reports upstream version
out2=$(install-catalog --version)
echo "$out2" | grep -q "sgml-common version 0.6.3" || {
  echo "FAIL: install-catalog --version -> [$out2]"; exit 1; }
echo "PASS 2: install-catalog --version -> $out2"

# 3. install-catalog --help usage banner
out3=$(install-catalog --help)
echo "$out3" | grep -q "Usage" || { echo "FAIL: install-catalog --help"; exit 1; }
echo "PASS 3: install-catalog --help banner OK"

# 4. installed XML declaration + ISO entity data files exist and are non-empty
for f in "$sgmldir/xml.dcl" \
         "$sgmldir/xml-iso-entities-8879.1986/ISOnum.ent" \
         "$sgmldir/sgml-iso-entities-8879.1986/ISOlat1.ent"; do
  [ -s "$f" ] || { echo "FAIL: missing/empty $f"; exit 1; }
done
echo "PASS 4: xml.dcl + ISO entity data files present"

# 5. installed sgml.conf config is readable and non-empty
[ -s "$prefix/etc/sgml/sgml.conf" ] || { echo "FAIL: sgml.conf missing/empty"; exit 1; }
echo "PASS 5: sgml.conf present"

# 6. behavioral guard: upstream install-catalog hardcodes a writability check on
#    /etc/sgml (independent of the central-catalog argument); in a user sandbox it
#    must refuse cleanly with exit 2.
out6=$(install-catalog --add "$TMPDIR/c.cat" "$sgmldir/xml-iso-entities-8879.1986/catalog" 2>&1) && rc6=0 || rc6=$?
[ "$rc6" = "2" ] || { echo "FAIL: install-catalog guard rc=$rc6 (expected 2)"; exit 1; }
echo "$out6" | grep -q "/etc/sgml" || { echo "FAIL: unexpected guard message [$out6]"; exit 1; }
echo "PASS 6: install-catalog /etc/sgml writability guard OK (exit 2)"

echo "test sgml 0.6.3: 6/6 checks PASS"
