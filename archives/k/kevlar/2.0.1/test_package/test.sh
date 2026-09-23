#!/bin/sh
# test_package functional test for kevlar 2.0.1.
# Exercises real CLI usage: help, new site skeleton, build -> HTML output.
set -euo pipefail

BIN_DIR="$(dirname "$(command -v kevlar)")"
KEVLAR="$BIN_DIR/kevlar"
MD2HTML="$BIN_DIR/md2html"
RST2HTML="$BIN_DIR/rst2html"
TEST_PKG_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "== kevlar help =="
"$KEVLAR" help

echo "== kevlar new =="
# /tmp is read-only on the OHOS host; create the scratch dir in a writable
# location (test_package build cwd) so mktemp works hermetically.
SCRATCH="$(mktemp -d "${PWD}/kevlar-test.XXXXXX")"
cd "$SCRATCH"
"$KEVLAR" new demo-site

# The upstream default theme requires GH_LINK/TWTR_LINK custom tags in config.
cd demo-site
printf 'title=Demos\ntheme=listed-kevlar-theme\nGH_LINK=https://github.com/example\nTWTR_LINK=https://twitter.com/example\n' > config.ini

# Provide the theme templates locally (upstream clones the theme via git at
# `kevlar new` time; in the sandboxed CI we supply it so the build is hermetic).
mkdir -p templates/listed-kevlar-theme
cat > templates/listed-kevlar-theme/header.html <<'HTM'
<!DOCTYPE html>
<head><meta charset="UTF-8"><title>--TITLE--</title>
<nav class="navbar">
  <a href="index.html">--TITLE--</a>
  <a href="--GH_LINK--">GitHub</a>
</nav>
HTM
cat > templates/listed-kevlar-theme/footer.html <<'HTM'
<footer>kevlar demo</footer>
HTM
cat > templates/listed-kevlar-theme/post.html <<'HTM'
--HEADER--
--CONTENT--
--FOOTER--
HTM
cat > templates/listed-kevlar-theme/index.html <<'HTM'
--HEADER--
<ul class="listing">--LISTING--</ul>
--FOOTER--
HTM
cat > templates/listed-kevlar-theme/entry.html <<'HTM'
<li><a href="--PATH--">--TITLE--</a> <time>--DATE--</time></li>
HTM

echo "== kevlar build =="
"$KEVLAR" build
test -f dist/index.html || { echo "FAIL: dist/index.html missing"; exit 1; }
test -f dist/hello-world.html || { echo "FAIL: dist/hello-world.html missing"; exit 1; }
grep -q "Welcome to kevlar" dist/hello-world.html || { echo "FAIL: markdown content missing in output"; exit 1; }
grep -q "GitHub" dist/index.html || { echo "FAIL: header tag missing in index.html"; exit 1; }
echo "OK: site generated (dist/index.html, dist/hello-world.html)"

echo "== md2html =="
"$MD2HTML" posts/hello-world.md md-only.html
grep -q "Welcome to kevlar" md-only.html || { echo "FAIL: md2html output missing"; exit 1; }
echo "OK: md2html"

echo "== rst2html =="
"$RST2HTML" "$TEST_PKG_DIR/example.rst" rst-out.html
grep -q "Title" rst-out.html || { echo "FAIL: rst2html output missing heading"; exit 1; }
echo "OK: rst2html"

echo "PASS"
exit 0