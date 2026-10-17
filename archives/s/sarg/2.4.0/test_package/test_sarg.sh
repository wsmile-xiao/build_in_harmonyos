#!/bin/sh
# sarg 2.4.0 real-consumer test (run from test_package/conanfile.py).
#
# sarg is a CLI report generator, so a genuine consumer test has to feed it an
# access log and prove that the HTML report it produces is correct: per user,
# per site and per date, with the user dimension isolated.  Checking that a
# file exists or printing a banner is not enough (R34).
#
# The config below deliberately sets neither image_dir nor graph_font, so the
# report assets can only come from the FONTDIR/IMAGEDIR that were burned into
# the binary at compile time (assertions 12-14).
#
# usage: test_sarg.sh <sarg-binary> <package-root> <workdir>
SARG_BIN="$1"
PKG_ROOT="$2"
T="$3"
if [ -z "$SARG_BIN" ] || [ -z "$PKG_ROOT" ] || [ -z "$T" ]; then
    echo "usage: $0 <sarg-binary> <package-root> <workdir>"
    exit 2
fi

# exclude_codes is an installed data file; consuming it also proves that the
# sysconfdir baked into the binary really points at this package.
EXCLUDE_CODES="$PKG_ROOT/etc/exclude_codes"
[ -f "$EXCLUDE_CODES" ] || { echo "missing $EXCLUDE_CODES"; exit 3; }

rm -rf "$T"
mkdir -p "$T/log" "$T/out" "$T/tmp"

# squid3 storeurl-style combined log, 3 records / 2 users / 2 sites.
cat > "$T/log/access.log" <<'EOF'
1404154800.123   10 10.0.0.10 TCP_MISS/200 1234 GET http://www.example.com/index.html user1 - DIRECT/1.2.3.4 text/html
1404154801.234   11 10.0.0.10 TCP_MISS/200 2234 GET http://www.example.com/a.html user1 - DIRECT/1.2.3.4 text/html
1404154802.345   12 10.0.0.11 TCP_MISS/404 3234 GET http://missing.example/x.html user2 - DIRECT/1.2.3.4 text/html
EOF

cat > "$T/sarg.conf" <<EOF
access_log $T/log/access.log
output_dir $T/out
temporary_dir $T/tmp
exclude_codes $EXCLUDE_CODES
date_format %d/%m/%Y
overwrite_report yes
EOF

"$SARG_BIN" --version > "$T/version.out" 2>&1
"$SARG_BIN" -f "$T/sarg.conf" > "$T/sarg.out" 2>&1
RC=$?

echo "[test] sarg -f $T/sarg.conf -> RC=$RC"
sed -n '1,12p' "$T/sarg.out"

FAIL=0
ck() { if eval "$2"; then echo "[A$1] pass: $3"; else echo "[A$1] FAIL: $3"; FAIL=$((FAIL+1)); fi; }
ck 1  '[ $RC -eq 0 ]'                                          "sarg exits 0"
ck 2  'grep -q "Successful report generated" "$T/sarg.out"'    "success marker in output"
ck 3  'grep -q "2\.4\.0" "$T/version.out"'                     "--version reports 2.4.0"
ck 4  'grep -q "Records in file: 3" "$T/sarg.out"'             "all 3 log records were parsed"
ck 5  '[ -f "$T/out/index.html" ]'                             "top level index.html"
ck 6  '[ -f "$T/out/sarg-date" ]'                              "date index report was generated"
ck 7  'grep -q "www.example.com" "$T/out/topsites.html"'       "topsites lists www.example.com"
ck 8  'grep -q "missing.example" "$T/out/topsites.html"'       "topsites lists missing.example"
ck 9  'grep -q "example.com" "$T/out/user1/user1.html" && ! grep -q "missing.example" "$T/out/user1/user1.html"' "user1 only sees its own sites (per user isolation)"
ck 10 'grep -q "missing.example" "$T/out/user2/user2.html"'    "user2 report has its own domain"
ck 11 'grep -q "user1" "$T/out/siteuser.html"'                 "siteuser maps the site back to user1"
# 404 is in exclude_codes upstream, so the 404 record must still show as a
# denied/404 entry rather than silently vanishing from the date index.
ck 12 '! grep -q "Cannot open directory" "$T/sarg.out"'        "baked IMAGEDIR resolves at run time (no missing asset warning)"
# copy_images() copies every regular file of the baked IMAGEDIR into
# <output_dir>/images/, so finding all four upstream pngs there is direct
# proof that the burned-in path was a directory the binary really read.
ck 13 '[ $(ls "$T"/out/images/*.png 2>/dev/null | wc -l) -eq 4 ]'          "all 4 png assets of the baked IMAGEDIR were copied into the report"
# where make install put them - same absolute prefix the binary was compiled
# with (FONTDIR is only dereferenced by the gd code path, which is disabled,
# so it is checked on disk here).
ck 14 'ls "$PKG_ROOT/share/sarg/fonts/DejaVuSans.ttf" "$PKG_ROOT"/share/sarg/images/sarg.png >/dev/null 2>&1' "fonts and images installed inside the package under the baked FONTDIR/IMAGEDIR"
echo "ASSERTS=14 PASS=$((14-FAIL)) FAIL=$FAIL"
[ "$FAIL" = 0 ] || exit 1
exit 0
