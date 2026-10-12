#!/usr/bin/env bash
set -euo pipefail

echo "[test] gs --version"
version=$(gs --version)
printf '%s\n' "$version"
case "$version" in
  10.07.1*) echo "PASS 1/2 gs --version" ;;
  *) echo "unexpected gs version: $version" >&2; exit 1 ;;
esac

cat > cli-page.ps <<'PS'
%!PS-Adobe-3.0
%%Pages: 1
%%BoundingBox: 0 0 200 200
%%Page: 1 1
0.9 0.2 0.15 setrgbcolor
30 30 140 140 rectfill
showpage
%%EOF
PS

gs -dSAFER -dBATCH -dNOPAUSE -sDEVICE=png16m -r72 -sOutputFile=cli-page.png cli-page.ps
printf '\211PNG\r\n\032\n' > png.sig
head -c 8 cli-page.png > png.got
cmp png.sig png.got
size=$(wc -c < cli-page.png | tr -d ' ')
if [ "$size" -lt 500 ]; then
  echo "cli png too small: $size" >&2
  exit 1
fi
echo "PASS 2/2 gs cli rendered one page bytes=$size"
