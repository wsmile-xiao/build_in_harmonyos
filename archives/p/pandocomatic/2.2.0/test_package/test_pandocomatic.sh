#!/bin/bash
# pandocomatic test_package runtime smoke (R34 real runtime).
set -e

echo "== pandocomatic --version =="
pandocomatic --version > version.txt 2>&1 || {
  cat version.txt
  exit 1
}
grep -q "version 2.2.0" version.txt || {
  echo "FAIL: version string not found"
  cat version.txt
  exit 1
}
echo "version check PASS"

echo "== pandocomatic --help =="
pandocomatic --help > help.txt 2>&1 || {
  cat help.txt
  exit 1
}
grep -qi "usage" help.txt || {
  echo "FAIL: usage string not found"
  cat help.txt
  exit 1
}
echo "help check PASS"

echo "== markdown -> HTML conversion =="
printf '# Hello HarmonyOS\n\nSome **bold** text.\n' > sample.md
pandocomatic -i sample.md -o sample.html > conv.log 2>&1 || {
  cat conv.log
  exit 1
}
[ -f sample.html ] || {
  echo "FAIL: sample.html not produced"
  cat conv.log
  exit 1
}
grep -q "<h1" sample.html || {
  echo "FAIL: HTML heading not found"
  cat sample.html
  exit 1
}
grep -q "Hello HarmonyOS" sample.html || {
  echo "FAIL: content not found"
  cat sample.html
  exit 1
}
echo "conversion check PASS"
echo "pandocomatic test package: OK"
exit 0
