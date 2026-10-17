#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke test for bsdsfv executable
# Runs in conanrun env (PATH includes installed bin/)
# P2 fix: -o pipefail prevents silent pipeline failures (audit)
set -euo pipefail

# OHOS: /tmp is read-only (E002), use TMPDIR instead
TMPDIR="${TMPDIR:-$HOME/tmp}"
WORK="$TMPDIR/bsdsfv_test_$$"
mkdir -p "$WORK"
cd "$WORK"

echo "[test] bsdsfv version"
bsdsfv -v 2>&1 | grep -q "1.18" && echo "OK version" || { echo "FAIL version"; exit 1; }

echo "[test] create SFV"
printf 'alpha content 1234567890\n' > alpha.txt
printf 'beta content ABCDEFGHIJ\n' > beta.txt
bsdsfv -c -a check.sfv alpha.txt beta.txt
grep -q "alpha.txt" check.sfv && grep -q "beta.txt" check.sfv && echo "OK create" || { echo "FAIL create"; exit 1; }

echo "[test] verify SFV (all OK)"
out=$(bsdsfv -T check.sfv)
echo "$out" | grep -q "2 OK - 0 bad" && echo "OK verify" || { echo "FAIL verify: $out"; exit 1; }

echo "[test] tamper detection (1 bad)"
printf 'tampered content!!!' > alpha.txt
# -T exits non-zero on BAD/MISSING; capture output without tripping set -e
out=$(bsdsfv -T check.sfv || true)
echo "$out" | grep -q "1 bad" && echo "OK tamper" || { echo "FAIL tamper: $out"; exit 1; }

echo "[test] missing detection (1 missing)"
printf 'alpha content 1234567890\n' > alpha.txt
rm -f beta.txt
out=$(bsdsfv -T check.sfv || true)
echo "$out" | grep -q "1 missing" && echo "OK missing" || { echo "FAIL missing: $out"; exit 1; }

echo "[test] all bsdsfv tests passed"
rm -rf "$WORK"
exit 0
