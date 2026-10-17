#!/usr/bin/env bash
# test_package/test_sqlite_rsync.sh — functional test for the sqlite3_rsync executable.
# Runs in the conanrun env, so PATH includes the installed bin/ (i.e. sqlite3_rsync).
#
# Every step is fail-able: any sync failure, data mismatch or regression in the
# argv hardening patch aborts the script with a non-zero exit (no WARN degradation).
set -euo pipefail

RSYNC="sqlite3_rsync"   # resolved from PATH via the conanrun environment

echo "[1] sqlite3_rsync --version"
"$RSYNC" --version

echo "[2] create source database (100 rows)"
WORKDIR="$(mktemp -d "${TMPDIR:-.}/rsync-test.XXXXXX")"
trap 'rm -rf "$WORKDIR"' EXIT
DB_SRC="$WORKDIR/src.db"
DB_DST="$WORKDIR/dst.db"
python3 - "$DB_SRC" <<'PYEOF'
import sqlite3, sys
con = sqlite3.connect(sys.argv[1])
con.execute("CREATE TABLE t(id INTEGER PRIMARY KEY, val TEXT)")
con.executemany("INSERT INTO t(val) VALUES(?)", [(f"row-{i}",) for i in range(100)])
con.commit()
con.close()
PYEOF

echo "[3] local sync round-trip (spawns replica side via popen2//bin/sh)"
"$RSYNC" "$DB_SRC" "$DB_DST"
test -s "$DB_DST" || { echo "FAIL: replica $DB_DST missing/empty after sync" >&2; exit 1; }

echo "[4] assert replica content matches source"
python3 - "$DB_SRC" "$DB_DST" <<'PYEOF'
import sqlite3, sys
src = sqlite3.connect(sys.argv[1])
dst = sqlite3.connect(sys.argv[2])
n_src, = src.execute("SELECT count(*) FROM t").fetchone()
n_dst, = dst.execute("SELECT count(*) FROM t").fetchone()
assert n_src == 100, f"source row count unexpected: {n_src}"
assert n_dst == n_src, f"replica row count mismatch: src={n_src} dst={n_dst}"
v_src, = src.execute("SELECT val FROM t WHERE id=42").fetchone()
v_dst, = dst.execute("SELECT val FROM t WHERE id=42").fetchone()
assert v_src == v_dst == "row-41", f"row 42 mismatch: {v_src!r} vs {v_dst!r}"
src.close()
dst.close()
print(f"replica verified: {n_dst} rows, spot-check OK")
PYEOF

echo "[5] unknown option must be rejected (argv hardening backport regression check)"
if "$RSYNC" -bogus-option "$DB_SRC" "$DB_DST" 2>"$WORKDIR/err.txt"; then
    echo "FAIL: -bogus-option was accepted as an argument" >&2
    exit 1
fi
grep -q "unknown option" "$WORKDIR/err.txt" || {
    echo "FAIL: expected 'unknown option' error, got: $(cat "$WORKDIR/err.txt")" >&2
    exit 1
}

echo "sqlite-rsync test_package: PASS"
