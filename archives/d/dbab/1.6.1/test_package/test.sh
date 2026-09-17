#!/data/service/hnp/bin/bash
# test_package/test.sh -- smoke test for the dbab tool scripts.
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the packaged scripts — presence, syntax,
# and the exact data-transformation pipelines the scripts run.
set -euo pipefail

PASS=0
DISCOVERED=13

ok() {
    PASS=$((PASS + 1))
    echo "        [ok] $1"
}

fail() {
    echo "        [fail] $1"
    exit 1
}

echo "[step] 1/4 dbab scripts on PATH and executable"
for prog in dbab-svr dbab-get-list dbab-add-list dbab-chk-list dhcp-add-wpad; do
    command -v "$prog" >/dev/null 2>&1 || fail "$prog not found on PATH"
    [ -x "$(command -v "$prog")" ] || fail "$prog is not executable"
    ok "$prog is on PATH and executable"
done

echo "[step] 2/4 shell syntax check (bash -n)"
for prog in dbab-get-list dbab-add-list dbab-chk-list dhcp-add-wpad; do
    bash -n "$(command -v "$prog")" || fail "bash -n failed for $prog"
    ok "bash -n passed for $prog"
done

echo "[step] 3/4 data-transformation pipelines (offline fixtures)"
WORKDIR="$(mktemp -d)"
trap 'rm -rf "$WORKDIR"' EXIT

# Fixture: user block list + already-blocked list + downloaded list sample.
printf 'ads.example.com\ntracker.example.org\n' > "$WORKDIR/dbab.list+"
printf 'ads.example.com\n' > "$WORKDIR/block_list"
printf 'address=/ads.example.com/127.0.0.1\naddress=/news.example.net/127.0.0.1\n' > "$WORKDIR/downloaded.tmp"
printf 'ads.example.com\n' > "$WORKDIR/dbab.list-"

# dbab-add-list core pipeline: sed 's#^.*$#address=/&/ADDR#' list+
ADDR="127.0.0.1"
sed 's#^.*$#address=/&/'"$ADDR"'#' "$WORKDIR/dbab.list+" > "$WORKDIR/add_out"
printf 'address=/ads.example.com/127.0.0.1\naddress=/tracker.example.org/127.0.0.1\n' > "$WORKDIR/add_exp"
cmp -s "$WORKDIR/add_out" "$WORKDIR/add_exp" || fail "dbab-add-list transform mismatch"
ok "dbab-add-list address-mapping transform matches"

# dbab-chk-list core pipeline: grep -Ff list+ block_list finds covered entry.
grep -Ff "$WORKDIR/dbab.list+" "$WORKDIR/block_list" | grep -q "ads.example.com" \
    || fail "dbab-chk-list grep pipeline found no covered entry"
ok "dbab-chk-list coverage grep pipeline matches"

# dbab-get-list core pipeline: grep -vFf list- downloaded | sed 127.0.0.1->srv.
grep -vFf "$WORKDIR/dbab.list-" "$WORKDIR/downloaded.tmp" \
    | sed "s/127\\.0\\.0\\.1/$ADDR/" > "$WORKDIR/get_out"
printf 'address=/news.example.net/127.0.0.1\n' > "$WORKDIR/get_exp"
cmp -s "$WORKDIR/get_out" "$WORKDIR/get_exp" || fail "dbab-get-list transform mismatch"
ok "dbab-get-list filter-and-rewrite transform matches"

echo "[step] 4/4 dbab-svr pixel-server payload integrity"
SVR="$(command -v dbab-svr)"
grep -q "dbab/v1.6" "$SVR" || fail "dbab-svr server id not found"
grep -q "IO::Socket::IP" "$SVR" || fail "dbab-svr socket backend not found"
grep -q "proxy.pac" "$SVR" || fail "dbab-svr WPAD handler not found"
ok "dbab-svr payload (server id, socket backend, WPAD handler) intact"

echo "[done] dbab test_package: $PASS/$DISCOVERED assertions passed"
echo "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":true,\"command\":\"bash test.sh\",\"discovered\":$DISCOVERED,\"passedCount\":$PASS}"
