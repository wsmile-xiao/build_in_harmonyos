#!/usr/bin/env bash
# omega/2.0.0 L1 smoke test (test_package source, R34).
# End-to-end: package CLIs report their version, scriptindex builds a
# one-record Xapian database, and the omega CGI answers a real query
# against it.  Every assertion below fails the suite via pipefail/grep -q.
set -euo pipefail

omega --version      | grep -q "omega - xapian-omega 2.0.0"
omindex --version    | grep -q "omindex - xapian-omega 2.0.0"
scriptindex --version | grep -q "scriptindex - xapian-omega 2.0.0"

# 1. Index a single document through scriptindex (indexer round trip).
printf 'text : index\n' > indexscript
printf 'text=the quick brown fox jumps over the lazy dog\n' \
    | scriptindex testdb indexscript > /dev/null

# 2. Query the database through the omega CGI binary (search round trip).
#    Template prints $querydescription: proves parameter parsing,
#    database opening and query compilation all executed for real.
printf '$querydescription\n' > tmpl1
cat > omega.conf <<'EOF'
database_dir .
template_dir .
log_dir .
default_template tmpl1
default_db testdb
EOF
OMEGA_CONFIG_FILE=omega.conf omega 'P=quick brown fox' \
    | grep -q "Query((Zquick@1 AND Zbrown@2 AND Zfox@3))"

echo "omega smoke OK"
