#!/usr/bin/env bash
set -euo pipefail

echo "== ykpersonalize -V =="
ykpersonalize -V 2>&1 | grep -Eq '(^|[^0-9.])1\.20\.0([^0-9.]|$)'

echo "== ykinfo -V =="
ykinfo -V 2>&1 | grep -Eq '(^|[^0-9.])1\.20\.0([^0-9.]|$)'

echo "== ykchalresp -V =="
ykchalresp -V 2>&1 | grep -Eq '(^|[^0-9.])1\.20\.0([^0-9.]|$)'

echo "All ykpers test_package assertions passed."
