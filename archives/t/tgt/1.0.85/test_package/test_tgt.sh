#!/usr/bin/env bash
# Consumer test for the tgt package - exercises the installed CLI surface.
# Runs entirely from the installed package folder: no daemon, no network.
set -e

BIN_DIR="$1"
TEST_DIR="$2"

if [ -z "${BIN_DIR:-}" ] || [ -z "${TEST_DIR:-}" ]; then
    echo "Usage: $0 <bin_dir> <test_dir>"
    exit 1
fi

for b in tgtd tgtadm tgtimg; do
    test -x "$BIN_DIR/$b" || { echo "FAIL: $BIN_DIR/$b missing"; exit 1; }
done

mkdir -p "$TEST_DIR"
cd "$TEST_DIR"

echo "=== Test 1: tgtd version ==="
"$BIN_DIR/tgtd" --version | head -1

echo "=== Test 2: tgtadm version ==="
"$BIN_DIR/tgtadm" --version | head -1

echo "=== Test 3: tgtd help ==="
"$BIN_DIR/tgtd" --help | grep -q "Usage: tgtd"

echo "=== Test 4: tgtimg help ==="
"$BIN_DIR/tgtimg" --help | grep -q "Usage: tgtimg"

echo "=== Test 5: tgtimg creates and reads back a tape image ==="
"$BIN_DIR/tgtimg" --op new --device-type tape --barcode=CONSUMER1 \
    --size=8 --type=data --file="$TEST_DIR/consumer1"
test -s "$TEST_DIR/consumer1"
"$BIN_DIR/tgtimg" --op show --file="$TEST_DIR/consumer1" > "$TEST_DIR/show.txt"
grep -q "CONSUMER1" "$TEST_DIR/show.txt"

echo "=== Test 6: tgtadm rejects a request when no daemon is listening ==="
# Proves the IPC code path is really linked and executed (not a stub): with
# TGT_IPC_SOCKET pointed at a non-existent socket, tgtadm must fail.
if TGT_IPC_SOCKET="$TEST_DIR/no-such.socket" "$BIN_DIR/tgtadm" \
        --lld iscsi --mode target --op show > "$TEST_DIR/no_daemon.txt" 2>&1; then
    echo "FAIL: tgtadm unexpectedly succeeded without a daemon"
    exit 1
else
    echo "    tgtadm failed as expected (rc=$?) when no daemon is listening"
    cat "$TEST_DIR/no_daemon.txt"
fi

echo "PASS: all tgt consumer tests passed"
