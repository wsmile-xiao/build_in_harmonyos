#!/data/service/hnp/bin/bash
# test_package/test_pktanon.sh — functional L1 test for the pktanon binary.
#
# R34: this genuinely exercises the tested package. pktanon parses an XML
# profile (Xerces-C++), reads the input pcap, applies the (identity) profile
# and writes the anonymized output pcap. We assert exit code 0, an output
# file with the pcap magic and the "anonymization done" marker.
#
# Runs from the test_package source dir (conan test_type=explicit).
set -u

SCRIPT_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)

# --- temporary working directory ------------------------------------------
WORKDIR=$(mktemp -d "${TMPDIR:-/tmp}/pktanon-test.XXXXXX") || {
    echo "FAIL: cannot create temp workdir"; exit 1; }
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

# --- tiny Ethernet/IPv4/TCP pcap (94 bytes) -------------------------------
# magic 0xa1b2c3d4 (LE), version 2.4, snaplen 65535, linktype 1 (Ethernet),
# then one 54-byte record (eth14 + ip20 + tcp20).
base64 -d > "$WORKDIR/in.pcap" <<'PCAP'
1MOyoQIABAAAAAAAAAAAAP//AAABAAAAAPFTZQAAAAA2AAAANgAAAAARIjNEVWZ3iJmquwgARQAAKBI0QABABgAACgAAAQoAAAIE0gBQAAAAAQAAAABQGCAAAAAAAA==
PCAP
[ -s "$WORKDIR/in.pcap" ] || { echo "FAIL: could not create in.pcap"; exit 1; }

# --- profile (full upstream identity settings) with relative paths --------
cp "$SCRIPT_DIR/profile.xml" "$WORKDIR/profile.xml" || { echo "FAIL: profile.xml missing"; exit 1; }

# --- run pktanon -----------------------------------------------------------
cd "$WORKDIR" || exit 1
if ! command -v pktanon >/dev/null 2>&1; then
    echo "FAIL: pktanon not found in PATH"; exit 1
fi
LOG=$(pktanon profile.xml 2>&1)
RC=$?
echo "$LOG"

[ "$RC" -eq 0 ] || { echo "FAIL: pktanon exited $RC"; exit 1; }
echo "$LOG" | grep -q "anonymization done" || {
    echo "FAIL: 'anonymization done' not reported"; exit 1; }

# --- validate output pcap ---------------------------------------------------
if [ ! -s out.pcap ]; then
    echo "FAIL: out.pcap not produced (or empty)"; exit 1
fi
MAGIC=$(od -An -N4 -tx1 out.pcap | tr -d ' \n')
[ "$MAGIC" = "d4c3b2a1" ] || {
    echo "FAIL: out.pcap bad magic ($MAGIC)"; exit 1; }

echo "OK: pktanon anonymized 1 packet -> out.pcap ($(wc -c < out.pcap) bytes, magic $MAGIC)"
exit 0
