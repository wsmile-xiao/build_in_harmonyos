#!/bin/bash
# test_tinydns.sh -- functional test for the tinydns family.
#
# The assertions deliberately run the *delivered* binaries against a real
# artifact instead of merely checking that a file exists:
#
#   1. tinydns-data compiles a .data source into a real CDB (data.cdb)
#   2. tinydns-get reads that CDB back and must report the A record we wrote
#   3. an absent name must produce no answer, so (2) cannot pass trivially
#   4. all five delivered binaries must be on PATH
#
# NOTE on the data-file syntax: in djbdns .data files a leading '&' declares a
# name together with the A record of its name server, which is the form that
# tinydns-get can actually read back. A leading '=' only delegates a zone
# (it yields no A record for the queried name), so it cannot be used here.
set -euo pipefail

fail() { echo "ERROR: $*" >&2; exit 1; }

echo "=== tinydns functional test ==="

TEST_DIR=$(mktemp -d)
trap 'rm -rf "$TEST_DIR"' EXIT
cd "$TEST_DIR"

# --- 1. the five binaries this package delivers must all be runnable -------
for cmd in tinydns-conf tinydns tinydns-data tinydns-get tinydns-edit; do
    command -v "$cmd" >/dev/null 2>&1 || fail "$cmd not found on PATH (package incomplete)"
    echo "  [ok] $cmd present: $(command -v "$cmd")"
done

# --- 2. tinydns-data must build a real CDB from a .data source ------------
# '&' = name + A record of its name server (readable back by tinydns-get)
cat > data << 'DATAFILE'
&example.com:127.0.0.1
DATAFILE

echo "Created data file:"
cat data

[ -f data ] || fail "data source file was not created"
[ ! -e data.tmp ] || fail "stale data.tmp left behind before the run"

tinydns-data || fail "tinydns-data exited non-zero (exit $?)"
echo "  [ok] tinydns-data ran successfully"

[ -f data.cdb ] || fail "data.cdb was not created by tinydns-data"
[ -s data.cdb ] || fail "data.cdb is empty"
[ ! -e data.tmp ] || fail "data.tmp was not renamed to data.cdb"

cdb_size=$(wc -c < data.cdb)
echo "  [ok] data.cdb created, ${cdb_size} bytes"

# A genuine CDB starts with the cdb_make header (0x5f, 0x08). Checking the
# magic rejects a stub or truncated file that a size test would accept.
cdb_magic=$(head -c 2 data.cdb | od -An -tx1 | tr -d ' \n')
[ "$cdb_magic" = "5f08" ] || fail "data.cdb is not a real CDB (magic=$cdb_magic, want 5f08)"
echo "  [ok] data.cdb has valid CDB magic (5f08)"

# --- 3. tinydns-get must read the record back out of the real CDB ---------
# NOTE the argument order: tinydns-get takes <type> <name>, not <name> <type>.
lookup=$(tinydns-get a example.com) || fail "tinydns-get a example.com exited non-zero"
echo "tinydns-get a example.com returned:"
echo "$lookup" | sed 's/^/    /'

echo "$lookup" | grep -q 'noerror' \
    || fail "tinydns-get did not report a noerror response"
echo "$lookup" | grep -qE 'A 127\.0\.0\.1' \
    || fail "tinydns-get did not return the A record 127.0.0.1 we compiled into the CDB"
echo "  [ok] A record 127.0.0.1 read back from the real CDB"

# --- 4. negative control: an absent name must yield no answer ------------
# This is what stops the assertion in step 3 from passing for any input.
absent=$(tinydns-get a nosuch-name.invalid) \
    || fail "tinydns-get a nosuch-name.invalid exited non-zero"
if echo "$absent" | grep -qE 'A 127\.0\.0\.1'; then
    fail "tinydns-get returned an A record for a name that is not in the CDB"
fi
echo "  [ok] absent name correctly yields no A record"

# --- 5. argument order is part of the CLI contract ----------------------
# Reversed arguments must be rejected rather than silently mis-parsed.
if tinydns-get example.com a >/dev/null 2>&1; then
    fail "tinydns-get accepted reversed arguments (expected usage error)"
fi
echo "  [ok] tinydns-get rejects reversed <name> <type> arguments"

echo "=== All tests passed ==="
exit 0
