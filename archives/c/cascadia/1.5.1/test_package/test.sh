#!/bin/sh
# test_package test.sh - cascadia 1.5.1 consumer test (POSIX sh, no $() / pipes).
# OHOS preflight mounts /tmp read-only; /bin/sh implements $(...) via /tmp
# temp files and `printf | cascadia` pipelines raise SIGPIPE (exit 141).
# This script uses only TMPDIR files + redirections: zero command
# substitutions, zero backticks, zero pipes. 3 real end-to-end assertions.
set -eu

tmpd="${TMPDIR:-}"
if [ -z "$tmpd" ]; then tmpd="${TMP:-}"; fi
if [ -z "$tmpd" ]; then tmpd="${TEMP:-}"; fi
if [ -z "$tmpd" ]; then tmpd="."; fi
mkdir -p "$tmpd"
cd "$tmpd"

if [ "$#" -ne 1 ]; then
    echo "usage: test.sh <path-to-cascadia>" >&2
    exit 2
fi

cascadia_bin="$1"

if [ ! -f "$cascadia_bin" ]; then
    echo "cascadia binary not found:" "$cascadia_bin" >&2
    exit 1
fi

echo "[step] Testing cascadia help..."
rm -f cas_help.txt
"$cascadia_bin" --help > cas_help.txt 2>&1
if ! grep -F "CSS" cas_help.txt > /dev/null; then
    echo "help check FAILED: CSS marker not found" >&2
    exit 1
fi
echo "        [ok] help check passed"

echo "[step] Testing cascadia single-element CSS extraction..."
rm -f cas_in1.html cas_out1.html
printf '%s' '<input type="radio" name="Sex" value="F" />' > cas_in1.html
"$cascadia_bin" -i cas_in1.html -o cas_out1.html -c 'input[name=Sex][value=F]' -q
if ! grep -F 'name="Sex"' cas_out1.html > /dev/null; then
    echo "css extraction FAILED: name attribute missing" >&2
    exit 1
fi
if ! grep -F 'value="F"' cas_out1.html > /dev/null; then
    echo "css extraction FAILED: value attribute missing" >&2
    exit 1
fi
echo "        [ok] css extraction check passed"

echo "[step] Testing cascadia ATTR piece extraction..."
rm -f cas_in3.html cas_out3.html
printf '%s' '<ul><li><a id="home" href="/index">Home</a></li><li><a id="about" href="/about">About</a></li></ul>' > cas_in3.html
"$cascadia_bin" -i cas_in3.html -o cas_out3.html -c 'li > a' -p 'id=ATTR:id' -q
if ! grep -F "home" cas_out3.html > /dev/null; then
    echo "piece extraction FAILED: home missing" >&2
    exit 1
fi
if ! grep -F "about" cas_out3.html > /dev/null; then
    echo "piece extraction FAILED: about missing" >&2
    exit 1
fi
echo "        [ok] piece extraction check passed"

echo "[ok] All tests passed."
