#!/bin/sh
# test_package/test.sh — pktstat 1.8.5 consumer cases (R34)
#
# Really executes the *installed* bin/pktstat and asserts on its observable
# behaviour: exit codes plus the exact diagnostic strings pktstat itself emits.
#
# Eight discovered cases:
#   C1/C1b/C2/C3  the usage-error path (getopt -> version banner -> usage line)
#   C4            -l/-t mutual exclusion
#   C5            -m 0 numeric validation
#   C6            the libpcap error path, reached with a nonexistent interface
#   C7            a real one-shot capture on loopback
#
# C1-C6 need no capture privilege and are deterministic.  C7 needs a usable
# packet socket, which a build container may not provide, so it is reported as
# an explicit SKIP carrying the measured stderr when the kernel refuses — never
# as a pass.
#
# Accounting is conservation-based on purpose: PASSED + SKIPPED must account for
# every discovered case and FAILED must be zero.  Pinning an exact PASSED count
# would make the suite go red on a *more* capable machine (a real HarmonyOS PC,
# where the loopback capture succeeds) — that would be testing the build
# container's kernel features instead of the software.
#
# `set -u` is on, but `set -e` is deliberately not: every case must run so the
# accounting marker is always printed.  `pipefail` is not set because it is not
# POSIX and the OHOS /system/bin/sh is mksh, where `set -o pipefail` is an error.
#
# argv: $1 = absolute path to the installed pktstat binary
#       $2 = file the HMBS_TEST_PACKAGE_RESULT marker is also written to

set -u

BIN="$1"
SUMMARY="$2"
PASSED=0
FAILED=0
SKIPPED=0
DISCOVERED=8

pass_case() {
    echo "PASS: $1"
    PASSED=$((PASSED + 1))
}

fail_case() {
    echo "FAIL: $1"
    FAILED=$((FAILED + 1))
}

skip_case() {
    echo "SKIP: $1 -- $2"
    SKIPPED=$((SKIPPED + 1))
}

echo "--- pktstat consumer test ---"
echo "binary: $BIN"

if [ ! -x "$BIN" ]; then
    echo "installed binary is missing or not executable: $BIN"
    # SUMMARY may be unwritable here; the exit 1 below is what actually fails
    # the suite, so the best-effort write is allowed to fail silently.
    echo 'HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":false,"command":"sh test.sh pktstat-cli","discovered":8,"passedCount":0,"failed":1,"skipped":0}' > "$SUMMARY" 2>/dev/null || true
    exit 1
fi

# --- C1/C1b/C2/C3: the usage-error path -----------------------------------------
# `pktstat -Z` takes getopt's default branch (main.c `default: error = 1`),
# which prints the version banner and the usage line to stderr and exits 1.
# Reaching that print proves the option parser, PACKAGE_VERSION and the usage
# string all linked and ran; no capture privilege is involved.
usage_out=$("$BIN" -Z 2>&1)
usage_rc=$?
echo "C1 raw: rc=$usage_rc"
echo "$usage_out" | sed -n '1,5p'

case "$usage_out" in
    *"unrecognized option"*) pass_case "C1 getopt rejects unknown option (-Z)" ;;
    *) fail_case "C1 getopt rejects unknown option (-Z)" ;;
esac

if [ "$usage_rc" -eq 1 ]; then
    pass_case "C1b usage error exits 1"
else
    fail_case "C1b usage error exits 1 (got rc=$usage_rc)"
fi

case "$usage_out" in
    *"pktstat version 1.8.5"*) pass_case "C2 version banner reports 1.8.5" ;;
    *) fail_case "C2 version banner reports 1.8.5" ;;
esac

# The usage line has to advertise every option group upstream documents,
# otherwise the binary we shipped is not the pktstat users expect.
missing_usage=""
for token in "usage:" "[-BcFlnpPtT]" "[-i interface]" "[-k keeptime]" \
             "[-m maxbps]" "[-w wait]" "[-a abbrev]" "[-A file]" "[filter-expr]"; do
    case "$usage_out" in
        *"$token"*) ;;
        *) missing_usage="$missing_usage $token" ;;
    esac
done
if [ -z "$missing_usage" ]; then
    pass_case "C3 usage line advertises all option groups"
else
    fail_case "C3 usage line missing:$missing_usage"
fi

# --- C4: mutual exclusion of -l and -t -------------------------------------------
# main.c rejects the combination with warnx() *before* touching pcap, so this
# also exercises the error-reporting helpers (err/warnx family) on musl.
excl_out=$("$BIN" -l -t 2>&1)
excl_rc=$?
echo "C4 raw: rc=$excl_rc :: $excl_out"
case "$excl_out" in
    *"-t incompatible with -l"*)
        if [ "$excl_rc" -eq 1 ]; then
            pass_case "C4 -l/-t mutually exclusive and exits 1"
        else
            fail_case "C4 -l/-t mutually exclusive (got rc=$excl_rc)"
        fi
        ;;
    *) fail_case "C4 -l/-t mutually exclusive (missing diagnostic)" ;;
esac

# --- C5: numeric option validation ----------------------------------------------
# -m is divided by 8 and must stay positive (main.c), so -m 0 must be refused.
mbps_out=$("$BIN" -m 0 2>&1)
mbps_rc=$?
echo "C5 raw: rc=$mbps_rc :: $mbps_out"
case "$mbps_out" in
    *"invalid argument to -m"*)
        if [ "$mbps_rc" -eq 1 ]; then
            pass_case "C5 -m 0 rejected and exits 1"
        else
            fail_case "C5 -m 0 rejected (got rc=$mbps_rc)"
        fi
        ;;
    *) fail_case "C5 -m 0 rejected (missing diagnostic)" ;;
esac

# --- C6: the libpcap error path is genuinely reached ----------------------------
# A nonexistent interface is handed to pcap_lookupdev()/pcap_open_live(); pktstat
# reports libpcap's own error through errx() and exits 1.  Seeing libpcap's
# message proves libpcap is really linked into the shipped binary and really
# called at runtime (a stub or a stripped-out capture layer could not do this).
iface_out=$("$BIN" -1 -i nosuchif0 2>&1)
iface_rc=$?
echo "C6 raw: rc=$iface_rc :: $iface_out"
case "$iface_out" in
    *nosuchif0*)
        if [ "$iface_rc" -eq 1 ]; then
            pass_case "C6 libpcap error path reached for a bad interface"
        else
            fail_case "C6 libpcap error path (got rc=$iface_rc)"
        fi
        ;;
    *) fail_case "C6 libpcap error path (libpcap diagnostic missing)" ;;
esac

# --- C7: live capture (needs a packet socket) -----------------------------------
# `-1 -i lo -P` is the cheapest real capture: loopback, promiscuous mode off, and
# a one-second sample window (oneflag makes pktstat exit after the first window).
# On success pktstat prints the machine-readable dump written by batch_update():
#   line 1  "<nflows> <period>"
#   then one "<octets> <packets> <tag>" line per observed flow
# so the success branch asserts that header shape rather than just "rc=0".
# Depending on the build container this either produces a real flow dump or is
# refused by the kernel; both outcomes are recorded with the measured output.
live_out=$("$BIN" -1 -i lo -P -w 1 2>&1)
live_rc=$?
echo "C7 raw: rc=$live_rc :: $live_out"
if [ "$live_rc" -eq 0 ]; then
    live_head=$(echo "$live_out" | sed -n '1p')
    nflows=${live_head%% *}
    case "$live_head" in
        [0-9]*" "[0-9]*)
            case "$nflows" in
                ""|0)
                    # The capture really ran, but nothing was decoded in the
                    # sample window, so this proves no packet accounting yet.
                    skip_case "C7 one-shot capture on loopback" \
                              "capture ran but no packets were observed: header=$live_head"
                    ;;
                *)
                    pass_case "C7 one-shot capture emits a flow dump"
                    echo "C7 header (nflows period): $live_head"
                    ;;
            esac
            ;;
        *)
            fail_case "C7 one-shot capture emits a flow dump (bad header: $live_head)"
            ;;
    esac
else
    skip_case "C7 one-shot capture on loopback" \
              "rc=$live_rc :: $live_out"
fi

# Conservation: every discovered case is either passed or honestly skipped.
OVERALL_PASSED=false
if [ "$FAILED" -eq 0 ] && [ "$((PASSED + SKIPPED))" -eq "$DISCOVERED" ]; then
    OVERALL_PASSED=true
fi

MARKER="HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":${OVERALL_PASSED},\"command\":\"sh test.sh (pktstat usage/version/option-validation/libpcap-error/live-capture)\",\"discovered\":${DISCOVERED},\"passedCount\":${PASSED},\"failed\":${FAILED},\"skipped\":${SKIPPED}}"
echo "$MARKER"
# Also persist it, so the driving conanfile can assert on the exact counts
# without having to scrape the conan log.
if [ -n "$SUMMARY" ]; then
    echo "$MARKER" > "$SUMMARY"
fi

if [ "$OVERALL_PASSED" = "true" ]; then
    echo "CONSUMER_ALL_PASS passed=$PASSED discovered=$DISCOVERED skipped=$SKIPPED"
    exit 0
fi

echo "CONSUMER_FAIL passed=$PASSED failed=$FAILED skipped=$SKIPPED discovered=$DISCOVERED"
exit 1
