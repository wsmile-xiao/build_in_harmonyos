#!/bin/sh
# test_package/test.sh — sc 7.16-1.1.3 consumer checks (6 assertions).
# Usage: test.sh <package_folder> <writable_workdir>
set -u

PKG="$1"
WORK="$2"
SC="$PKG/bin/sc"
PSC="$PKG/bin/psc"
SCQREF="$PKG/bin/scqref"
XSC="$PKG/bin/xsc"
FAIL=0
RUN=0
discovered=6
passed=0

ok() { RUN=$((RUN + 1)); passed=$((passed + 1)); echo "ok - $1"; }
bad() { RUN=$((RUN + 1)); echo "FAIL - $1"; FAIL=1; }

mkdir -p "$WORK" "$WORK/home"
[ -x "$SC" ] || { echo "FAIL - $SC not executable"; exit 1; }
[ -x "$PSC" ] || { echo "FAIL - $PSC not executable"; exit 1; }

# 1) psc -v version anchor (prints rev to stderr, rc=0)
"$PSC" -v >"$WORK/psc-v.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "7.16_1.1.3" "$WORK/psc-v.out"; then
    ok "psc -v rc=0 and reports 7.16_1.1.3"
else
    bad "psc -v rc=$rc (see $WORK/psc-v.out)"
fi

# 2) psc plain-text to sc conversion
printf '10 20\n30 40\n' | "$PSC" >"$WORK/psc.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && grep -q "let A0 = 10" "$WORK/psc.out" && grep -q "let B0 = 20" "$WORK/psc.out"; then
    ok "psc converts plain text to let lines"
else
    bad "psc conversion rc=$rc (see $WORK/psc.out)"
fi

# 3) sc non-interactive table calculation via official -v -P pipe mode
# Upstream plain stdout redirect writes unevaluated expressions
# (let C0 = A0+B0), so grep 30 can never match there; -v valueizes
# expressions before put, yielding let C0 = 30. -P % selects the
# whole sheet (upstream range % = entire spreadsheet).
cp "$(dirname "$0")/fixture.sc" "$WORK/fixture.sc" || { echo "FAIL - fixture.sc unreadable"; exit 1; }
HOME="$WORK/home" "$SC" -v -P '%' "$WORK/fixture.sc" >"$WORK/sc.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$WORK/sc.out" ] && grep -q "let C0 = 30" "$WORK/sc.out"; then
    ok "sc non-interactive computes C0=A0+B0=30 rc=0"
else
    bad "sc compute rc=$rc (see $WORK/sc.out)"
fi

# 4) scqref quick reference runs
HOME="$WORK/home" "$SCQREF" < /dev/null >"$WORK/qref.out" 2>&1
rc=$?
if [ "$rc" -eq 0 ] && [ -s "$WORK/qref.out" ]; then
    ok "scqref runs rc=0 with non-empty output"
else
    bad "scqref rc=$rc (see $WORK/qref.out)"
fi

# 5) xsc wrapper script present and executable
if [ -x "$XSC" ] && [ -s "$XSC" ]; then
    ok "xsc wrapper present and executable"
else
    bad "xsc missing or empty"
fi

# 6) install tree completeness
missing=""
for f in bin/sc bin/psc bin/scqref bin/xsc share/sc/tutorial.sc share/man/man1/sc.1 licenses/LICENSE; do
    [ -s "$PKG/$f" ] || missing="$missing $f"
done
if [ -z "$missing" ]; then
    ok "install tree complete (bin x4 + tutorial + man + license)"
else
    bad "install tree missing:$missing"
fi

if [ "$FAIL" -eq 0 ]; then
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
else
    echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":false,\"command\":\"bash test.sh\",\"discovered\":${discovered},\"passedCount\":${passed}}"
    exit 1
fi
exit 0
