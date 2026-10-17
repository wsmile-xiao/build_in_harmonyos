#!/bin/bash
# test_package/run_pg_test.sh — tdigest 1.4.4 consumer + upstream regression test.
#
# Runs the packaged extension inside a real PostgreSQL 18.3 server that runs
# natively on OHOS PC:
#   1. copy the postgresql installation (bin/lib/share) into an isolated
#      workdir → the conan cache stays pristine and repeatable;
#   2. initdb + start the server (TCP only: the OHOS build has no unix sockets);
#   3. install the packaged tdigest.so + tdigest.control + tdigest--*.sql into
#      that isolated installation;
#   4. replay the *upstream* regression suite (test/sql + test/expected,
#      verbatim copies kept in test_package/) with pg_regress;
#   5. run OHOS-specific assertions.
#
# Usage: run_pg_test.sh <pg_bindir> <pkg_libdir> <pkg_sharedir> <tests_dir>
#
# No `set -e` on purpose: every failure is collected and reported together;
# the final non-zero-exit check is the real gate.
set -uo pipefail

PG_BINDIR="${1:?pg_bindir required}"
PKG_LIBDIR="${2:?pkg_libdir required}"
PKG_SHAREDIR="${3:?pkg_sharedir required}"
TESTS_DIR="${4:?tests_dir required}"

MODULE="$PKG_LIBDIR/tdigest.so"
CONTROL="$PKG_SHAREDIR/extension/tdigest.control"

# The 10 upstream regression tests, in upstream Makefile order
# (Makefile: REGRESS = basic copy cast conversions incremental parallel_query
#  value_count_api trimmed_aggregates combine_crash combine).
REGRESS="basic copy cast conversions incremental parallel_query value_count_api trimmed_aggregates combine_crash combine"

[ -f "$MODULE" ] || { echo "FAIL: tdigest.so not found in package libdir: $MODULE"; exit 1; }
[ -f "$CONTROL" ] || { echo "FAIL: tdigest.control not found in package sharedir"; exit 1; }
ls "$PKG_SHAREDIR/extension/"tdigest--*.sql >/dev/null 2>&1 || { echo "FAIL: tdigest--*.sql not found in package sharedir"; exit 1; }
[ -d "$TESTS_DIR/sql" ] || { echo "FAIL: upstream test tree not found: $TESTS_DIR/sql"; exit 1; }

# OHOS /tmp is a read-only erofs mount (E002): use a writable temp base.
TMPBASE="${TMPDIR:-$HOME/tmp}"
mkdir -p "$TMPBASE" || { echo "FAIL: cannot create $TMPBASE"; exit 1; }
WORKDIR="$(mktemp -d "$TMPBASE/tdigest-test-XXXXXX")" || { echo "FAIL: mktemp"; exit 1; }
PGROOT="$WORKDIR/pginstall"
DATADIR="$WORKDIR/data"
LOGFILE="$WORKDIR/server.log"
TESTDIR="$WORKDIR/testdir"

cleanup() {
    if [ -x "$PGROOT/bin/pg_ctl" ]; then
        "$PGROOT/bin/pg_ctl" -D "$DATADIR" stop -m immediate >/dev/null 2>&1 || true
    fi
    rm -rf "$WORKDIR"
}
trap cleanup EXIT

fail() { echo "FAIL: $*"; exit 1; }

# ── 1. isolated PostgreSQL installation ─────────────────────────────────────
PG_SRC_ROOT="$(dirname "$PG_BINDIR")"
mkdir -p "$PGROOT"
cp -r "$PG_SRC_ROOT/bin" "$PG_SRC_ROOT/lib" "$PG_SRC_ROOT/share" "$PGROOT/" \
    || fail "cannot copy postgresql installation"
INITDB="$PGROOT/bin/initdb"; PGCTL="$PGROOT/bin/pg_ctl"
PSQL="$PGROOT/bin/psql";     PG_CONFIG="$PGROOT/bin/pg_config"
for bin in "$INITDB" "$PGCTL" "$PSQL" "$PG_CONFIG"; do
    [ -x "$bin" ] || fail "required PostgreSQL binary missing after copy: $bin"
done

"$INITDB" -D "$DATADIR" -U postgres --no-locale -E UTF8 >"$WORKDIR/initdb.log" 2>&1 \
    || { echo "FAIL: initdb failed"; tail -20 "$WORKDIR/initdb.log"; exit 1; }

# ── 2. install the packaged extension into the isolated installation ────────
PKGLIBDIR="$("$PG_CONFIG" --pkglibdir)" || fail "pg_config --pkglibdir"
SHAREDIR="$("$PG_CONFIG" --sharedir)"   || fail "pg_config --sharedir"
PGXS="$("$PG_CONFIG" --pgxs)"           || fail "pg_config --pgxs"
case "$PKGLIBDIR" in "$PGROOT"*) ;; *) fail "pg_config not relocatable: $PKGLIBDIR";; esac
cp "$MODULE" "$PKGLIBDIR/tdigest.so" || fail "cannot install tdigest.so"
mkdir -p "$SHAREDIR/extension"
cp "$CONTROL" "$SHAREDIR/extension/" || fail "cannot install tdigest.control"
cp "$PKG_SHAREDIR/extension/"tdigest--*.sql "$SHAREDIR/extension/" || fail "cannot install SQL scripts"

# ── 3. start the server ─────────────────────────────────────────────────────
PORT=$(( (RANDOM % 20000) + 40000 ))
"$PGCTL" -D "$DATADIR" -l "$LOGFILE" \
    -o "-p $PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=''" \
    -w -t 60 start || { echo "FAIL: server did not start (port $PORT)"; tail -20 "$LOGFILE"; exit 1; }

export PGHOST=127.0.0.1 PGPORT="$PORT" PGUSER=postgres
q() { "$PSQL" -X -h 127.0.0.1 -p "$PORT" -U postgres -d "${2:-postgres}" -t -A -c "$1"; }

# ── 4. replay the upstream regression suite ─────────────────────────────────
mkdir -p "$TESTDIR/sql" "$TESTDIR/expected" "$TESTDIR/tmp"
cp "$TESTS_DIR/sql/"*.sql "$TESTDIR/sql/"        || fail "cannot stage upstream sql/"
cp "$TESTS_DIR/expected/"*.out "$TESTDIR/expected/" || fail "cannot stage upstream expected/"
# the upstream scripts \i-include the extension SQL by relative name
cp "$SHAREDIR/extension/"tdigest--*.sql "$TESTDIR/" || fail "cannot stage extension SQL"
# OHOS adaptation (E002): upstream test/sql/copy.sql hardcodes /tmp, which is a
# read-only mount here. Only the path literal is rewritten — in the script AND
# in its expected output, so the psql echo lines still match — the SQL logic is
# untouched. The files stored in test_package/ are byte-identical to upstream.
sed -i "s#/tmp/#$TESTDIR/tmp/#g" "$TESTDIR/sql/copy.sql" "$TESTDIR/expected/copy.out" \
    || fail "cannot adapt /tmp path for OHOS"
mkdir -p "$TESTDIR/tmp"

PG_REGRESS="$PGROOT/lib/postgresql/pgxs/src/test/regress/pg_regress"
[ -x "$PG_REGRESS" ] || fail "pg_regress not found: $PG_REGRESS"
# pg_regress' own RUNPATH is '$ORIGIN/../lib' (PG 18 is built with
# --enable-rpath and a '/' prefix); that resolves against bin/, not against its
# deep pgxs location, so libpq.so.5 must be reachable through LD_LIBRARY_PATH.
export LD_LIBRARY_PATH="$PGROOT/lib${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}"

echo "── upstream regression suite (pg_regress) ──"
( cd "$TESTDIR" && "$PG_REGRESS" --inputdir="$TESTDIR" --outputdir="$TESTDIR" \
    --bindir="$PGROOT/bin" --dbname=contrib_regression $REGRESS ) \
    >"$WORKDIR/pg_regress.log" 2>&1
REGRESS_RC=$?
cat "$WORKDIR/pg_regress.log"

UP_TOTAL=$(grep -cE '^(ok|not ok) ' "$WORKDIR/pg_regress.log")
UP_PASS=$(grep -cE '^ok ' "$WORKDIR/pg_regress.log")
UP_FAIL=$((UP_TOTAL - UP_PASS))
if [ "$REGRESS_RC" -ne 0 ]; then
    echo "FAIL: pg_regress exited $REGRESS_RC"
    [ -f "$TESTDIR/regression.diffs" ] && head -80 "$TESTDIR/regression.diffs"
fi

echo "── OHOS-specific assertions ──"
OHOS_PASS=0
OHOS_TOTAL=0
ohos() {  # ohos <description> <0|1 result>
    OHOS_TOTAL=$((OHOS_TOTAL + 1))
    if [ "$2" -eq 0 ]; then OHOS_PASS=$((OHOS_PASS + 1)); echo "PASS: $1"; else echo "FAIL: $1"; fi
}

# OH-1: the packaged module dlopens inside the OHOS-native postgres process
q "DROP DATABASE IF EXISTS tdigest_ohos;" >/dev/null 2>&1
q "CREATE DATABASE tdigest_ohos;" >/dev/null 2>&1
q "CREATE EXTENSION tdigest;" tdigest_ohos >"$WORKDIR/oh1.log" 2>&1
rc=$?
n=$(q "SELECT count(*) FROM pg_extension WHERE extname='tdigest';" tdigest_ohos 2>/dev/null)
[ "$rc" -eq 0 ] && [ "$n" = "1" ]; ohos "OH-1 CREATE EXTENSION tdigest loads the module in the OHOS postgres server (pg_extension rows=$n)" $?

# OH-2: platform ABI of the shipped module — AArch64, and the only DT_NEEDED
# entry is libc; no glibc-only dependency and no build-machine rpath.
READELF="$(command -v readelf || command -v llvm-readelf || true)"
if [ -n "$READELF" ]; then
    machine="$("$READELF" -h "$MODULE" 2>/dev/null | awk -F: '/Machine/{gsub(/ /,"",$2);print $2}')"
    needed="$("$READELF" -d "$MODULE" 2>/dev/null | awk '/NEEDED/{gsub(/[][]/,"",$NF);print $NF}' | sort -u | tr '\n' ' ')"
    runpath="$("$READELF" -d "$MODULE" 2>/dev/null | awk '/RUNPATH|RPATH/{print $0}')"
    [ "$machine" = "AArch64" ] && [ "$needed" = "libc.so " ] && [ -z "$runpath" ]
    ohos "OH-2 module ABI: machine=$machine needed=[$needed] rpath=[${runpath:-none}]" $?
else
    ohos "OH-2 module ABI check skipped (no readelf/llvm-readelf on this host)" 1
fi

# OH-3: /tmp read-only workaround actually round-trips data (text + binary).
# Mirrors upstream test/sql/copy.sql: 5 digests are built with the upstream
# PL/pgSQL INSERT pattern (a loop variable keeps `i` out of the aggregate).
"$PSQL" -X -h 127.0.0.1 -p "$PORT" -U postgres -d tdigest_ohos -q -v ON_ERROR_STOP=1 \
    >"$WORKDIR/oh3.log" 2>&1 <<'SQL'
CREATE TABLE src(id int, s tdigest);
DO $$
DECLARE i int;
BEGIN
  FOR i IN 1..5 LOOP
    INSERT INTO src SELECT i, tdigest(random(), 100) FROM generate_series(1,1000) s(x);
  END LOOP;
END $$;
CREATE TABLE dst(id int, s tdigest);
SQL
oh3_rc=$?
q "COPY src TO '$TESTDIR/tmp/ohos_copy_text.out';" tdigest_ohos >>"$WORKDIR/oh3.log" 2>&1 || oh3_rc=1
q "COPY src TO '$TESTDIR/tmp/ohos_copy_bin.out' WITH (FORMAT BINARY);" tdigest_ohos >>"$WORKDIR/oh3.log" 2>&1 || oh3_rc=1
q "COPY dst FROM '$TESTDIR/tmp/ohos_copy_text.out';" tdigest_ohos >>"$WORKDIR/oh3.log" 2>&1 || oh3_rc=1
q "COPY dst FROM '$TESTDIR/tmp/ohos_copy_bin.out' WITH (FORMAT BINARY);" tdigest_ohos >>"$WORKDIR/oh3.log" 2>&1 || oh3_rc=1
rt="$(q "SELECT (SELECT count(*) FROM src) || '/' || (SELECT count(*) FROM dst) || '/' || (SELECT count(*) FROM src a JOIN dst b ON a.id=b.id AND a.s::text<>b.s::text);" tdigest_ohos 2>>"$WORKDIR/oh3.log")"
[ "$oh3_rc" -eq 0 ] && [ "$rt" = "5/10/0" ]
ohos "OH-3 OHOS /tmp workaround round-trip: src/dst/mismatch = $rt (expected 5/10/0)" $?
[ "$oh3_rc" -eq 0 ] || cat "$WORKDIR/oh3.log"

# OH-4: a real aggregate query returns sane quantiles through the packaged module
pv="$(q "SELECT round(tdigest_percentile(x, 100, 0.5)::numeric, 6) FROM (SELECT i/1000.0 AS x FROM generate_series(0,1000) s(i)) d;" tdigest_ohos 2>/dev/null)"
[ -n "$pv" ] && awk -v v="$pv" 'BEGIN{exit !(v > 0.45 && v < 0.55)}'
ohos "OH-4 tdigest_percentile(median) ~ 0.5 on 0..1 data (got $pv)" $?

echo
echo "RESULT: upstream regression $UP_PASS/$UP_TOTAL passed (failed=$UP_FAIL); OHOS assertions $OHOS_PASS/$OHOS_TOTAL passed"
[ "$REGRESS_RC" -eq 0 ] && [ "$UP_TOTAL" -eq 10 ] && [ "$UP_PASS" -eq 10 ] && [ "$OHOS_PASS" -eq "$OHOS_TOTAL" ] || {
    echo "FAILED"; exit 1;
}
echo "ALL TESTS PASSED"
exit 0
