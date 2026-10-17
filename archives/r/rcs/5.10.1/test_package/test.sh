#!/bin/sh
# Real RCS semantics test: version assertions + a ci/co/rlog/rcsdiff/
# rcsmerge/ident round trip against a real ,v repository.
#
# NB: deliberately avoids mkdir/cd — freshly created directories on
# HMDFS are not immediately enterable, and the test folder is fresh.
set -eu

export LOGNAME=rcs-tester
export USER=rcs-tester

: > output.txt

# -- 1. every installed command answers --version -------------------------
for tool in rcs ci co ident merge rcsclean rcsdiff rcsmerge rlog; do
    "$tool" --version >/dev/null
done
echo rcs-version-ok >> output.txt

# -- 2. ci/co round trip over two revisions -------------------------------
rm -f desc.txt demo.txt demo.txt,v

cat > desc.txt <<EOF
demo file for the consumer test
EOF
cat > demo.txt <<EOF
first line
EOF

ci -q -i -tdesc.txt -m"initial import" demo.txt </dev/null
co -q -l demo.txt
grep -q '^first line$' demo.txt && echo roundtrip-initial-ok >> output.txt

cat > demo.txt <<EOF
first line
second line
\$Id\$
EOF
ci -q -f -m"add second line" demo.txt </dev/null
rm -f demo.txt
co -q demo.txt
grep -q '^second line$' demo.txt && echo roundtrip-second-ok >> output.txt

# -- 3. check out the previous revision and compare -----------------------
rm -f demo.txt
co -q -r1.1 demo.txt
grep -q '^second line$' demo.txt && exit 1
grep -q '^first line$' demo.txt && echo checkout-rev1-ok >> output.txt

# -- 4. rcsdiff reports the 1.1 -> 1.2 delta ------------------------------
if rcsdiff -q -r1.1 -r1.2 demo.txt >/dev/null 2>&1; then
    exit 1
fi
rcsdiff -q -r1.1 -r1.2 demo.txt 2>/dev/null | grep -q '^> second line$' \
    && echo rcsdiff-delta-ok >> output.txt

# -- 5. rlog reports both revisions ---------------------------------------
rlog demo.txt 2>/dev/null | grep -q '^revision 1.2$' \
    && echo rlog-two-revisions-ok >> output.txt

# -- 6. ident sees the expanded Id keyword --------------------------------
rm -f demo.txt
co -q demo.txt
ident demo.txt 2>/dev/null | grep -q '\$Id:' && echo ident-keyword-ok >> output.txt

# -- 7. rcsclean considers the unlocked, unchanged file removable ----------
rm -f demo.txt
co -q demo.txt
rcsclean -n demo.txt 2>/dev/null | grep -q 'demo.txt' \
    && echo rcsclean-would-clean-ok >> output.txt

# -- 8. rcsmerge folds the 1.1 -> 1.2 delta onto a 1.1 base ---------------
rm -f demo.txt
co -q -r1.1 demo.txt
rcsmerge -q -r1.1 -r1.2 demo.txt 2>/dev/null
grep -q '^second line$' demo.txt && echo rcsmerge-fold-ok >> output.txt
