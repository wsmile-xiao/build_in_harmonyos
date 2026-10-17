#!/bin/sh
# Offline run-time verification for the installed uacme 1.8.1 binaries.
#
# uacme always links libcurl and exactly one TLS backend, and startup calls
# curl_version_info(CURLVERSION_NOW), so a binary that prints its version has
# really linked and initialised both. Nothing here needs the network: every
# ACME operation (new/issue/update/deactivate/newkey/revoke) requires a live
# ACME server, ualpn needs to bind port 443, and dns-01 needs real DNS
# updates, so none of that is attempted.
#
# Both binaries treat a version query as a NON-SUCCESS exit by upstream
# design: uacme's main() opens with `int ret = 2` (uacme.c:1536) and `case 'V'`
# prints the banner then jumps to the shared exit (uacme.c:1701-1703 -> 2076)
# without resetting it, while ualpn's `case 'V'` calls
# cleanup_and_exit(0, EXIT_FAILURE) (ualpn.c:4318-4320). The assertions below
# therefore check the printed version rather than the status.
set -u

BIN_DIR="${1:-}"

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

[ -n "$BIN_DIR" ] || fail "usage: test_uacme.sh <package>/bin"
[ -d "$BIN_DIR" ] || fail "bin directory not found: $BIN_DIR"
[ -x "$BIN_DIR/uacme" ] || fail "uacme binary missing or not executable"

uacme_version=$("$BIN_DIR/uacme" -V 2>&1)
echo "$uacme_version"
echo "$uacme_version" | grep -q "version 1.8.1" \
    || fail "uacme did not report version 1.8.1"

if [ -x "$BIN_DIR/ualpn" ]; then
    ualpn_version=$("$BIN_DIR/ualpn" -V 2>&1)
    echo "$ualpn_version"
    echo "$ualpn_version" | grep -q "version 1.8.1" \
        || fail "ualpn did not report version 1.8.1"
else
    echo "NOTE: ualpn not installed in this build"
fi

echo "PASS: installed uacme and ualpn start and report version 1.8.1"
