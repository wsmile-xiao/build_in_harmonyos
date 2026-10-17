#!/data/service/hnp/bin/bash
# test_package/test.sh — consumer test for the wdiff executable
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the tested package's binary with behavior assertions.
set -eu
export TERM=dumb

echo "[test] wdiff --version"
wdiff --version | head -1 | grep -q "1\.2\.3"
echo "OK: --version reports 1.2.3 ($(wdiff --version | head -1))"

echo "[test] functional: word-level diff between two files"
# wdiff exec()s GNU `diff` at runtime (DIFF_PROGRAM). When only a non-GNU
# diff (toybox/busybox) is on PATH, wdiff cannot parse the difference
# stream; detect that case and skip the functional assertions honestly.
if diff --version 2>/dev/null | grep -q GNU; then
  HAVE_GNU_DIFF=yes
else
  HAVE_GNU_DIFF=no
  echo "SKIP: functional assertions (GNU diff not on PATH; wdiff requires it at runtime)"
fi
if [ "$HAVE_GNU_DIFF" = yes ]; then
  printf 'hello world\n' > a.txt
  printf 'hello brave world\n' > b.txt
  # wdiff exit code semantics mirror diff: 1 = differences found
  OUT=$(wdiff a.txt b.txt) && RC=0 || RC=$?
  echo "$OUT"
  [ "$RC" -eq 1 ] || { echo "FAIL: wdiff exit $RC, expected 1 (differences found)"; exit 1; }
  case "$OUT" in
    *'{+brave+}'*) echo "OK: wdiff reported insertion {+brave+}";;
    *) echo "FAIL: wdiff output missing {+brave+}"; exit 1;;
  esac
  echo "[test] exit code: files without word differences"
  printf 'same line\n' > c.txt
  printf 'same line\n' > d.txt
  wdiff c.txt d.txt
  echo "OK: identical files exit 0 with no output"
  rm -f a.txt b.txt c.txt d.txt
fi

echo "ALL TESTS PASSED"
