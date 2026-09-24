#!/bin/bash
# Functional test for postgresql-url_encode 1.2.3 (R34/R51).
#
# Runs the extension inside a real PostgreSQL 18.3 server:
#   copy the postgresql package (bin/lib/share) into an isolated
#   workdir → initdb → install url_encode.so + control + sql into that
#   copy → start server → CREATE EXTENSION → execute the 5 upstream
#   test statements (test/sql/url_encode.sql) via psql and assert the
#   exact outputs recorded in test/expected/url_encode.out.
#
# The isolated copy keeps the conan cache pristine (repeatable runs,
# CI L1e re-testing) — postgres binaries and pg_config are relocatable,
# so the copied install works from any path.
#
# Usage: run_pg_test.sh <pg_bindir> <pkg_libdir> <pkg_sharedir>
# No `set -e` on purpose: assertions are collected and reported together;
# the final [ "$PASS" -eq "$TOTAL" ] check is the real pass/fail gate.
set -uo pipefail

PG_BINDIR="${1:?pg_bindir required}"
PKG_LIBDIR="${2:?pkg_libdir required}"
PKG_SHAREDIR="${3:?pkg_sharedir required}"

MODULE="$PKG_LIBDIR/url_encode.so"
if [ ! -f "$MODULE" ]; then
    echo "FAIL: url_encode.so not found in package libdir: $MODULE"
    exit 1
fi
if [ ! -f "$PKG_SHAREDIR/extension/url_encode.control" ]; then
    echo "FAIL: url_encode.control not found in package sharedir"
    exit 1
fi
if ! ls "$PKG_SHAREDIR/extension/"url_encode--*.sql >/dev/null 2>&1; then
    echo "FAIL: extension SQL script not found in package sharedir"
    exit 1
fi

# OHOS /tmp is read-only (E002): use a writable temp directory.
TMPBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPBASE" || { echo "FAIL: cannot create $TMPBASE"; exit 1; }
WORKDIR="$(mktemp -d "$TMPBASE/urlenc-test-XXXXXX")" || { echo "FAIL: mktemp"; exit 1; }
DATADIR="$WORKDIR/data"
LOGFILE="$WORKDIR/server.log"
PGROOT="$WORKDIR/pginstall"

cleanup() {
    if [ -x "$PGROOT/bin/pg_ctl" ]; then
        "$PGROOT/bin/pg_ctl" -D "$DATADIR" stop -m immediate >/dev/null 2>&1 || true
    fi
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

fail() { echo "FAIL: $*"; exit 1; }

# Isolated PostgreSQL installation: copy bin/lib/share out of the
# conan cache (skip include/ — not needed at runtime).
PG_SRC_ROOT="$(dirname "$PG_BINDIR")"
mkdir -p "$PGROOT"
cp -r "$PG_SRC_ROOT/bin" "$PG_SRC_ROOT/lib" "$PG_SRC_ROOT/share" "$PGROOT/" \
    || fail "cannot copy postgresql installation"

INITDB="$PGROOT/bin/initdb"
PGCTL="$PGROOT/bin/pg_ctl"
PSQL="$PGROOT/bin/psql"
PG_CONFIG="$PGROOT/bin/pg_config"
for bin in "$INITDB" "$PGCTL" "$PSQL" "$PG_CONFIG"; do
    [ -x "$bin" ] || fail "required PostgreSQL binary missing after copy: $bin"
done

"$INITDB" -D "$DATADIR" -U postgres --no-locale -E UTF8 >"$WORKDIR/initdb.log" 2>&1 \
    || fail "initdb failed, see $WORKDIR/initdb.log"

# Install the extension into the isolated installation (pg_config in
# the copy reports paths inside $PGROOT).
PKGLIBDIR="$("$PG_CONFIG" --pkglibdir)" || fail "pg_config --pkglibdir"
SHAREDIR="$("$PG_CONFIG" --sharedir)" || fail "pg_config --sharedir"
case "$PKGLIBDIR" in "$PGROOT"*) ;; *) fail "pg_config not relocatable: $PKGLIBDIR";; esac
cp "$MODULE" "$PKGLIBDIR/url_encode.so" || fail "cannot install url_encode.so into $PKGLIBDIR"
mkdir -p "$SHAREDIR/extension"
cp "$PKG_SHAREDIR/extension/url_encode.control" "$SHAREDIR/extension/" || fail "cannot install control file"
cp "$PKG_SHAREDIR/extension/"url_encode--*.sql "$SHAREDIR/extension/" || fail "cannot install SQL script"

# Start the server on a non-default port (avoid CI collisions).
PORT=$(( (RANDOM % 20000) + 40000 ))
"$PGCTL" -D "$DATADIR" -l "$LOGFILE" -o "-p $PORT" -w -t 60 start \
    || { echo "FAIL: server did not start (port $PORT)"; tail -20 "$LOGFILE"; exit 1; }

q() {  # q <sql> — run one query, print tuples-only unaligned output
    "$PSQL" -X -h 127.0.0.1 -p "$PORT" -U postgres -d postgres -t -A -c "$1"
}

PASS=0
TOTAL=0
check() {  # check <description> <sql> <expected>
    TOTAL=$((TOTAL + 1))
    got="$(q "$2")"
    if [ "$got" = "$3" ]; then
        PASS=$((PASS + 1))
        echo "PASS: $1"
    else
        echo "FAIL: $1"
        echo "  expected: [$3]"
        echo "  got:      [$got]"
    fi
}

# CREATE EXTENSION must succeed: proves the module loads into the
# server (dlopen of url_encode.so + PG module magic check) and the SQL
# objects register.
TOTAL=$((TOTAL + 1))
if q "CREATE EXTENSION url_encode;" >/dev/null 2>&1 && \
   [ "$(q "SELECT count(*) FROM pg_extension WHERE extname = 'url_encode';")" = "1" ]; then
    PASS=$((PASS + 1))
    echo "PASS: CREATE EXTENSION url_encode"
else
    echo "FAIL: CREATE EXTENSION url_encode"
fi

# Statement 1 of upstream test/sql/url_encode.sql
check "url_encode('Hello World')" \
    "SELECT url_encode('Hello World');" \
    "Hello%20World"

# Statement 2
check "url_decode('Hello%20World')" \
    "SELECT url_decode('Hello%20World');" \
    "Hello World"

# Statement 3 — returns 5 rows; compare the full result block with
# test/expected/url_encode.out (second row is the empty path element)
TOTAL=$((TOTAL + 1))
GOT3="$(q "SELECT url_encode(unnest) from unnest(string_to_array('http://hu.wikipedia.org/wiki/São_Paulo','/'));")"
EXP3="http%3A

hu.wikipedia.org
wiki
S%C3%A3o_Paulo"
if [ "$GOT3" = "$EXP3" ]; then
    PASS=$((PASS + 1))
    echo "PASS: url_encode(unnest) — 5 rows"
else
    echo "FAIL: url_encode(unnest) — 5 rows"
    echo "  expected: [$EXP3]"
    echo "  got:      [$GOT3]"
fi

# Statement 4
check "uri_encode full URL" \
    "SELECT uri_encode('http://hu.wikipedia.org/wiki/São_Paulo');" \
    "http://hu.wikipedia.org/wiki/S%C3%A3o_Paulo"

# Statement 5 — md5 over the decoded UTF-8 URL
check "md5(uri_decode(...))" \
    "SELECT md5(uri_decode('http://hu.wikipedia.org/wiki/S%C3%A3o_Paulo'));" \
    "147ded7d471df9cf050bc13242cbf39e"

echo "RESULT: $PASS/$TOTAL assertions passed"
[ "$PASS" -eq "$TOTAL" ] || exit 1
exit 0
