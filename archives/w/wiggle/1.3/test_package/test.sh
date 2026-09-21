#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for wiggle 1.3
# Runs in conanrun env (PATH includes installed bin/).
# Real behavioural scenario: extract a diff, merge a patch, assert exact output.
set -eu

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
cd "$scratch"
# bash trusts PWD over a failed getcwd() syscall; seed it for HMDFS dirs.
PWD="$(pwd)"
export PWD

printf 'alpha\nbravo\ncharlie\n' > orig
printf -- '--- orig\n+++ new\n@@ -1,3 +1,3 @@\n alpha\n-bravo\n+BRAVO\n charlie\n' > patch
printf 'alpha\nBRAVO\ncharlie\n' > expected

echo "[test] wiggle --version"
# the banner goes to stderr, so merge streams before grepping
wiggle --version 2>&1 | grep -q "wiggle 1.3" || { echo "❌ --version output mismatch"; exit 1; }
echo "✅ --version reports wiggle 1.3"

echo "[test] wiggle -m orig patch (clean merge to stdout)"
wiggle -m orig patch > merged
cmp merged expected || { echo "❌ merged output differs from expected"; exit 1; }
if grep -q '<<<<<<<' merged; then echo "❌ unexpected conflict markers"; exit 1; fi
echo "✅ merge output matches expected exactly, no conflict markers"

echo "[test] wiggle -dw orig expected (change display extraction)"
wiggle -dw orig expected > ext.diff || true
# wiggle -d exits diff(1)-style code 1 when files differ, and -w emits wiggle's
# annotated change display (removed as <<<--old-->>>, added as <<<++new++>>>),
# not a unified diff; assert the annotation markers.
grep -q '<<<++BRAVO++>>>' ext.diff || { echo "❌ extraction lacks the added BRAVO marker"; exit 1; }
grep -q '<<<--bravo-->>>' ext.diff || { echo "❌ extraction lacks the removed bravo marker"; exit 1; }
echo "✅ extraction shows bravo→BRAVO as an annotated change"

echo "wiggle consumer test: all assertions passed"
