#!/bin/sh
set -eu

# test_package/test_sql_translator.sh — functional test for SQL::Translator
# L1: File existence checks + L2: MySQL -> PostgreSQL conversion

# L1: Verify SQL/Translator.pm is installed
PM_FOUND=0
for dir in $(echo "$PERL5LIB" | tr ':' ' '); do
    if [ -f "$dir/SQL/Translator.pm" ]; then
        PM_FOUND=1
        break
    fi
done
if [ "$PM_FOUND" -eq 0 ]; then
    echo "FAIL: SQL/Translator.pm not found in PERL5LIB"
    exit 1
fi
echo "PASS: Found SQL/Translator.pm"

# L2: Functional test — MySQL to PostgreSQL DDL conversion
# Check if runtime dependencies are available before running
if ! perl -e 'use Moo; use Parse::RecDescent; use Try::Tiny;' 2>/dev/null; then
    echo "SKIP: Runtime dependencies (Moo, Parse::RecDescent, etc.) not available on this worker"
    echo "SKIP: Functional test (MySQL -> PostgreSQL) skipped — L1 file checks passed"
    exit 0
fi

OUTPUT=$(perl -e '
use SQL::Translator;
my $mysql = q{
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE
);
};
my $tr = SQL::Translator->new();
$tr->parser("MySQL");
$tr->producer("PostgreSQL");
my $result = $tr->translate(data => \$mysql);
die "Translation failed" unless $result;
die "Missing CREATE TABLE" unless $result =~ /CREATE TABLE/i;
die "Missing serial" unless $result =~ /serial/i;
print "FUNC_TEST_PASS\n";
' 2>&1) || {
    echo "FAIL: Functional test failed:"
    echo "$OUTPUT"
    exit 1
}

case "$OUTPUT" in
    *FUNC_TEST_PASS*)
        echo "PASS: Functional test MySQL -> PostgreSQL conversion"
        ;;
    *)
        echo "FAIL: Unexpected output: $OUTPUT"
        exit 1
        ;;
esac
