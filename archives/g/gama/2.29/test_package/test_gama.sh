#!/bin/bash
# Consumer test for gama: run the real gama-local binary end-to-end.
set -e

echo "== gama-local --version =="
gama-local --version

echo "== real adjustment on upstream traverse-01-en-left.gkf =="
gama-local traverse.gkf --algorithm svd --text out.txt --xml out.xml

echo "== assert structured XML result =="
[ -s out.xml ] || { echo "out.xml is empty"; exit 1; }
grep -q 'gama-local' out.xml || { echo "XML root missing"; exit 1; }
grep -q '<point' out.xml || { echo "adjusted points missing from XML"; exit 1; }
[ -s out.txt ] || { echo "out.txt is empty"; exit 1; }

echo "gama-local adjustment OK"
