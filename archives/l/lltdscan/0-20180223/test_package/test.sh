#!/data/service/hnp/bin/bash
# test_package/test.sh — functional smoke tests for the lltdscan executable.
#
# Runs inside the conanrun env (PATH includes the packaged bin/).
#
# lltdscan is a layer-2 scanner: with no -i it calls pcap_lookupdev(), sends a
# broadcast LLTD frame via libnet, then blocks in pcap_dispatch() for the
# -t timeout. So NEVER run a bare `lltdscan` here — it would open a promiscuous
# raw socket (needs root on a real device) and block for the full timeout.
#
# Every assertion below sticks to the deterministic command-line paths that
# return before any socket is opened: the getopt parser, the usage printer and
# the argument validator. Those exercise the real binary end to end without
# needing a NIC, root privileges or an LLTD responder on the wire.
set -uo pipefail

BIN="${LLTDSCAN_BIN:-lltdscan}"
TMP="${TMPDIR:-$HOME/tmp}/lltdscan-test-$$"
mkdir -p "$TMP"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "FAIL: $*"
    exit 1
}

# assert_usage <outfile> — the usage() banner that usage() prints.
# Note: upstream does `argc -= optind; argv += optind;` before its positional
# checks, so on the argc>1 path argv[0] is the first MAC, not the program name.
# Match only the option synopsis, which is identical on every path.
assert_usage() {
    grep -q "usage:.*\[-i iface\] \[-t timeout\] \[-u\] \[-v\] \[-v\] \[aa:bb:cc:dd:ee:ff\]" "$1" \
        || fail "usage banner missing the full option synopsis"
    grep -q "timeout is in milliseconds" "$1" || fail "usage banner missing timeout hint"
    grep -q "add -u to show machine names in UTF-8" "$1" || fail "usage banner missing -u hint"
    grep -q "add -v or -vv increase verbosity" "$1" || fail "usage banner missing -v hint"
    grep -q "last argument is an optional single MAC-address of interest" "$1" \
        || fail "usage banner missing trailing MAC argument hint"
}

# Test 1: `-h` is the documented help switch; it prints usage() and exits 0
# without opening a socket (the 'h' case calls usage() then exit(EXIT_SUCCESS)).
# Here argv[0] is still the program path, so the banner must also name lltdscan.
echo "[test] -h prints usage and exits 0"
"$BIN" -h > "$TMP/help.txt" 2>&1
rc=$?
[ "$rc" -eq 0 ] || fail "-h exited $rc, expected 0"
[ -s "$TMP/help.txt" ] || fail "-h produced empty output"
grep -q "usage:.*lltdscan \[-i iface\]" "$TMP/help.txt" || fail "-h banner does not name the program"
assert_usage "$TMP/help.txt"
echo "PASS: -h exit 0 + complete usage banner (8 assertions)"

# Test 2: an unknown option must be rejected. getopt prints
# "unrecognized option: Z" and the switch's default: branch exits
# EXIT_FAILURE without ever reaching libnet_init()/pcap_open_live().
echo "[test] unknown option -Z is rejected"
"$BIN" -Z > "$TMP/badopt.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "-Z exited $rc, expected 1"
grep -q "unrecognized option: Z" "$TMP/badopt.txt" || fail "-Z did not report an unrecognized option"
echo "PASS: -Z rejected with exit 1 (2 assertions)"

# Test 3: a missing option argument must be rejected the same way.
echo "[test] -t without its argument is rejected"
"$BIN" -t > "$TMP/noarg.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "-t (no arg) exited $rc, expected 1"
grep -q "option requires an argument: t" "$TMP/noarg.txt" || fail "-t did not report a missing argument"
echo "PASS: -t without argument rejected with exit 1 (2 assertions)"

# Test 4: the trailing MAC argument is validated for exact 17-character
# aa:bb:cc:dd:ee:ff form; a short one must be refused before any I/O.
echo "[test] malformed trailing MAC address is rejected"
"$BIN" aa:bb > "$TMP/badmac.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "malformed MAC exited $rc, expected 1"
grep -q "Invalid MAC-address: 'aa:bb'" "$TMP/badmac.txt" || fail "malformed MAC not reported"
echo "PASS: malformed MAC rejected with exit 1 (2 assertions)"

# Test 5: at most one trailing MAC is accepted; two fall into the argc > 1
# branch which prints usage() and exits EXIT_FAILURE.
echo "[test] two trailing MAC addresses print usage and exit 1"
"$BIN" aa:bb:cc:dd:ee:ff aa:bb:cc:dd:ee:ff > "$TMP/twomac.txt" 2>&1
rc=$?
[ "$rc" -eq 1 ] || fail "two MAC args exited $rc, expected 1"
assert_usage "$TMP/twomac.txt"
echo "PASS: two MAC args rejected with usage + exit 1 (6 assertions)"

echo "lltdscan: ALL PASS (5 cases / 20 assertions)"