#!/usr/bin/env bash
# test_package/test.sh — consumer test for the installed `jellyfish` CLI.
#
# Runs in the conanrun environment (the package's bin/ directory is on PATH).
# Every check is a real assertion against the packaged binary; the last two
# checks are negative controls asserting that invalid input is rejected.
set -euo pipefail

JF=${JELLYFISH_BIN:-jellyfish}
ASSERTIONS=0
FAILURES=0

pass() { ASSERTIONS=$((ASSERTIONS + 1)); echo "PASS: $1"; }
fail() { ASSERTIONS=$((ASSERTIONS + 1)); FAILURES=$((FAILURES + 1)); echo "FAIL: $1"; }
check_eq() { # <description> <actual> <expected>
    if [ "$2" = "$3" ]; then
        pass "$1"
    else
        fail "$1 (got: '$2', want: '$3')"
    fi
}

workdir=$(mktemp -d "${TMPDIR:-.}/jellyfish-test.XXXXXX" 2>/dev/null) || \
    workdir=$(mktemp -d "./jellyfish-test.XXXXXX")
trap 'rm -rf "$workdir"' EXIT
cd "$workdir"

cat > t.fa <<'EOF'
>s1
ACGTACGTACGT
>s2
ACGTACGTAAAA
EOF

# 1. version
if out=$("$JF" --version 2>/dev/null); then
    check_eq "jellyfish --version" "$out" "jellyfish 2.3.1"
else
    fail "jellyfish --version did not run"
fi

# 2. count canonical 5-mers
if "$JF" count -m 5 -s 100k -C -o out.jf t.fa >/dev/null 2>&1 && [ -s out.jf ]; then
    pass "jellyfish count produces a non-empty database"
else
    fail "jellyfish count did not produce out.jf"
fi

# 3. histogram (exact)
if out=$("$JF" histo out.jf 2>/dev/null | tr '\n' ';'); then
    check_eq "histo output" "$out" "1 3;6 1;7 1;"
else
    fail "jellyfish histo failed"
fi

# 4. dump (exact, canonical mers)
if out=$("$JF" dump -c out.jf 2>/dev/null | sort | tr '\n' ';'); then
    check_eq "dump -c output" "$out" "$(printf 'ACGTA 7\nCGTAA 1\nCGTAC 6\nGTAAA 1\nTAAAA 1\n' | tr '\n' ';')"
else
    fail "jellyfish dump failed"
fi

# 5. query an explicit mer
if out=$("$JF" query out.jf ACGTA 2>/dev/null); then
    check_eq "query ACGTA" "$out" "ACGTA 7"
else
    fail "jellyfish query ACGTA failed"
fi

# 6. query canonicalizes the reverse complement
if out=$("$JF" query out.jf TACGT 2>/dev/null); then
    check_eq "query TACGT canonicalized" "$out" "ACGTA 7"
else
    fail "jellyfish query TACGT failed"
fi

# 7. query against sequences read from a file
if out=$("$JF" query out.jf -s t.fa 2>/dev/null | wc -l | tr -d ' '); then
    check_eq "query -s line count" "$out" "16"
else
    fail "jellyfish query -s failed"
fi

# 8. query against sequences: number of ACGTA hits
if out=$("$JF" query out.jf -s t.fa 2>/dev/null | grep -c '^ACGTA 7$'); then
    check_eq "query -s ACGTA hits" "$out" "7"
else
    check_eq "query -s ACGTA hits" "0" "7"
fi

# 9. info reads the database header
if "$JF" info out.jf >/dev/null 2>&1; then
    pass "jellyfish info reads the database"
else
    fail "jellyfish info failed on out.jf"
fi

# 10. negative control: missing input file must be rejected
if "$JF" count -m 5 -s 100k -o bad.jf non_existent.fa >/dev/null 2>&1; then
    fail "count with a missing input file should have failed"
else
    pass "count rejects a missing input file"
fi

# 11. negative control: missing database must be rejected
if "$JF" histo no_such.jf >/dev/null 2>&1; then
    fail "histo with a missing database should have failed"
else
    pass "histo rejects a missing database"
fi

echo "ASSERTIONS: $ASSERTIONS, FAILURES: $FAILURES"
if [ "$FAILURES" -ne 0 ]; then
    exit 1
fi
exit 0
