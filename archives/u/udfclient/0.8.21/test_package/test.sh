#!/usr/bin/env bash
# test_package/test.sh — consumer end-to-end test for udfclient 0.8.21 (OHOS PC).
#
# Flow: usage banners of all six tools -> newfs_udf creates a UDF image ->
# udfdump scans the descriptors and mounts the volume set / dumps the tree ->
# udfclient mounts read-only and lists the fileset -> negative control.
#
# Each tool writes its output to a file which is then matched by grep; piping
# large outputs (udfdump -S emits ~600 KB) into `grep -q` makes the producer
# die with SIGPIPE / E2BIG once grep exits, which `set -o pipefail` would turn
# into a bogus test failure.
#
# This file is executed by test_package/conanfile.py via bash (OHOS
# /system/bin/sh cannot execute ELF binaries directly).
set -euo pipefail

require_grep() {
    local label="$1" pattern="$2" file="$3"
    if grep -q "$pattern" "$file"; then
        return 0
    fi
    echo "ERROR: $label (pattern not found: $pattern)"
    exit 1
}

rm -rf udfclient-consumer
mkdir udfclient-consumer
cd udfclient-consumer

echo "[test] usage banner of all six tools"
for tool in udfclient udfdump newfs_udf cd_sessions cd_disect mmc_format; do
    "$tool" > "usage-$tool.out" 2>&1 || true
    require_grep "$tool usage banner" "Usage" "usage-$tool.out"
done

echo "[test] newfs_udf creates a UDF image"
newfs_udf -L OHOSTESTVOL -b 2048 -s 8192 consumer.img >newfs.out 2>&1
test -s consumer.img

echo "[test] udfdump sequential scan finds the logical volume"
udfdump -S consumer.img >dumpS.out 2>&1 || true
require_grep "udfdump -S descriptor scan" "OHOSTESTVOL" dumpS.out

echo "[test] udfdump mounts the image: volume set, label and directory tree"
udfdump -b 2048 consumer.img >dump.out 2>&1 || true
require_grep "udfdump volume set" "Volume set" dump.out
udfdump -b 2048 -t consumer.img >dumpt.out 2>&1 || true
require_grep "udfdump -t volume label" "OHOSTESTVOL" dumpt.out
require_grep "udfdump -t directory tree" "Directory tree of mount point" dumpt.out

echo "[test] udfclient mounts read-only and lists the fileset"
printf 'ls\nexit\n' | udfclient -b 2048 consumer.img >client.out 2>&1 || true
require_grep "udfclient read-only mount" "Directory listing of /" client.out

echo "[test] negative control: udfdump must fail on a missing image"
if udfdump /nonexistent-udf-image >/dev/null 2>&1; then
    echo "ERROR: udfdump unexpectedly accepted a missing image"
    exit 1
fi

echo "ALL UDFCLIENT CONSUMER TESTS PASSED"
