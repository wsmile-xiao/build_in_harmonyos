#!/usr/bin/env bash
# Consumer test for pgreplay (runs with conanrun env: pgreplay on PATH,
# libpq resolvable via LD_LIBRARY_PATH).
set -euo pipefail

echo "[test] 1. parse a PostgreSQL stderr log into a replay file (-f)"
cat > sample.log <<'EOF'
2010-12-31 10:59:52.236 UTC|postgres|postgres|4d1db7a8.4236|LOG:  connection authorized: user=postgres database=postgres
2010-12-31 10:59:52.241 UTC|postgres|postgres|4d1db7a8.4236|LOG:  statement: set client_encoding to 'UTF8'
2010-12-31 10:59:52.241 UTC|postgres|postgres|4d1db7a8.4227|LOG:  connection authorized: user=postgres database=postgres
2010-12-31 10:59:52.243 UTC|postgres|postgres|4d1db7a8.4227|LOG:  statement: set client_encoding to 'LATIN9'
EOF
pgreplay -f -o out.rf sample.log 2> parse.err
echo "PASS: pgreplay -f exited 0"

echo "[test] 2. replay file is a non-empty binary stream"
test -s out.rf
if [ "$(head -c 4 out.rf | od -An -tx1 | tr -d ' \n')" = "00000000" ]; then
    echo "FAIL: replay file starts with zeroed header"
    exit 1
fi
echo "PASS: replay file written ($(wc -c < out.rf) bytes)"

echo "[test] 3. dry-run replay of the file (-r -n, no database connection)"
pgreplay -r -n -E UTF8 out.rf > dryrun.out 2> dryrun.err
grep -q "Replay statistics" dryrun.out
echo "PASS: dry-run replay produced statistics"

echo "ALL CONSUMER CHECKS PASSED"
