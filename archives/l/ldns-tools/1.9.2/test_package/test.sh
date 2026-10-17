#!/data/service/hnp/bin/bash
# test_package/test.sh - functional test for the ldns command line tools.
# Runs inside the conanrun env (PATH already contains the packaged bin/).
set -euo pipefail

SELF="${BASH_SOURCE[0]:-$0}"
DIR="$(cd "$(dirname "$SELF")" && pwd)"
cd "$DIR"

for tool in drill ldns-read-zone ldns-version ldns-keygen ldns-notify; do
    command -v "$tool" >/dev/null || { echo "$tool is not on PATH"; exit 1; }
done
echo "[test] tools found: drill ldns-read-zone ldns-version ldns-keygen ldns-notify"

# 1) version queries must exit 0
echo "[test] drill -v"
DRILL_OUT="$(drill -v 2>&1)"
case "$DRILL_OUT" in
    *drill*version*) echo "        [ok] $DRILL_OUT" ;;
    *) echo "unexpected drill -v output: $DRILL_OUT"; exit 1 ;;
esac

echo "[test] ldns-version"
LDNS_OUT="$(ldns-version)"
case "$LDNS_OUT" in
    1.9.2*) echo "        [ok] ldns version: $LDNS_OUT" ;;
    *) echo "unexpected ldns-version output: $LDNS_OUT"; exit 1 ;;
esac

# /tmp is read-only on OHOS - use a scratch dir under $HOME instead.
SCRATCH="${TMPDIR:-$HOME/tmp}"
[ -d "$SCRATCH" ] || mkdir -p "$SCRATCH"
TESTDIR="$SCRATCH/ldns-tools-test-$$"
mkdir -p "$TESTDIR"
trap 'rm -rf "$TESTDIR"' EXIT

# 2) offline zone-file round trip: no resolver, no network involved
cat > "$TESTDIR/example.zone" <<'ZONEEOF'
$ORIGIN example.com.
$TTL 3600
@	IN	SOA	ns.example.com. hostmaster.example.com. (
			2026091601 ; serial
			3600       ; refresh
			600        ; retry
			86400      ; expire
			3600 )     ; minimum
@	IN	NS	ns.example.com.
ns	IN	A	192.0.2.1
www	IN	A	192.0.2.2
ZONEEOF

echo "[test] ldns-read-zone example.zone"
OUT="$TESTDIR/example.zone.out"
ldns-read-zone "$TESTDIR/example.zone" > "$OUT"
grep -q "SOA" "$OUT" || { echo "no SOA record parsed"; cat "$OUT"; exit 1; }
grep -q "192.0.2.1" "$OUT" || { echo "NS glue address not parsed"; cat "$OUT"; exit 1; }
grep -q "example.com." "$OUT" || { echo "origin not expanded"; cat "$OUT"; exit 1; }
echo "        [ok] parsed $(wc -l < "$OUT") lines of zone data"

# 3) negative control: a missing zone file must not be reported as success
echo "[test] ldns-read-zone missing.zone (expected failure)"
if ldns-read-zone "$TESTDIR/missing.zone" >/dev/null 2>&1; then
    echo "ldns-read-zone reported success for a missing file"
    exit 1
fi
echo "        [ok] missing input rejected"

echo "All tests passed."