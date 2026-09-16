#!/bin/sh
# test_cgit.sh — cgit 3-assertion smoke (R34: executes the packaged cgit binary).
# 1. cgit --version reports cgit
# 2. cgit binary is a non-empty executable
# 3. CGI query against a fresh git repo returns HTML with repo content
set -eu

fail() {
  echo "FAIL: $1" >&2
  exit 1
}

command -v cgit >/dev/null 2>&1 || fail "cgit not on PATH"
cgit --version 2>&1 | grep -qi "cgit" || fail "cgit --version does not mention cgit"
echo "ok 1 - cgit --version"

CGIT_BIN=$(command -v cgit)
test -s "$CGIT_BIN" || fail "cgit binary is empty"
test -x "$CGIT_BIN" || fail "cgit binary is not executable"
echo "ok 2 - cgit binary non-empty executable"

WORK_BASE="${TMPDIR:-${TMP:-$HOME/tmp}}"
mkdir -p "$WORK_BASE" 2>/dev/null || true
WORK=$(mktemp -d "$WORK_BASE/cgit-test.XXXXXX" 2>/dev/null || mktemp -d 2>/dev/null || mktemp -d -t cgit-test)
trap 'rm -rf "$WORK"' EXIT INT TERM
REPO="$WORK/repo"
mkdir -p "$REPO"
git init -q "$REPO" || fail "git init failed"
git -C "$REPO" config user.email "cgit-test@example.com"
git -C "$REPO" config user.name "cgit-test"
git -C "$REPO" config commit.gpgsign false
echo "hello cgit" > "$REPO/hello.txt"
git -C "$REPO" add hello.txt || fail "git add failed"
git -C "$REPO" commit -qm "initial commit" || fail "git commit failed"
cat > "$WORK/cgitrc" <<EOF
virtual-root=/
cache-root=$WORK/cache
repo.url=test
repo.path=$REPO/.git
repo.desc=test repo
EOF
mkdir -p "$WORK/cache"
OUT="$WORK/out.html"
CGIT_CONFIG="$WORK/cgitrc" QUERY_STRING="url=test" cgit > "$OUT" 2>/dev/null || fail "cgit CGI query failed"
test -s "$OUT" || fail "cgit CGI output is empty"
grep -qi "test" "$OUT" || fail "cgit CGI output missing repo marker"
echo "ok 3 - cgit CGI query returns repo HTML"
echo "All 3 cgit smoke assertions passed"
