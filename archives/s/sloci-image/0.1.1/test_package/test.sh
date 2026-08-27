#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the sloci-image script
# Runs in conanrun env (PATH includes the installed bin/)
# R34: genuinely exercises the tested package's binary.
set -eu

echo "[step] sloci-image --version"
sloci-image --version | grep -q "sloci-image 0.1.1"
echo "        [ok] --version returns sloci-image 0.1.1"

echo "[step] sloci-image --help"
HELP_OUT=$(sloci-image --help 2>&1 || true)  # || true: sloci-image --help exits via SIGPIPE when output is piped
echo "$HELP_OUT" | grep -q "Usage"
echo "        [ok] --help shows usage"

echo "[step] sloci-image creates OCI image from rootfs"
TMPDIR_TEST=$(mktemp -d)
mkdir -p "$TMPDIR_TEST/rootfs"
echo "hello" > "$TMPDIR_TEST/rootfs/testfile"
cd "$TMPDIR_TEST"
sloci-image "$TMPDIR_TEST/rootfs" testimg:latest
# Verify OCI image structure was actually created
if [ ! -f "testimg/index.json" ]; then
    echo "        [fail] index.json not created"
    rm -rf "$TMPDIR_TEST"
    exit 1
fi
if [ ! -f "testimg/oci-layout" ]; then
    echo "        [fail] oci-layout not created"
    rm -rf "$TMPDIR_TEST"
    exit 1
fi
if [ ! -d "testimg/blobs/sha256" ]; then
    echo "        [fail] blobs/sha256 directory not created"
    rm -rf "$TMPDIR_TEST"
    exit 1
fi
BLOB_COUNT=$(find testimg/blobs/sha256 -type f | wc -l)
if [ "$BLOB_COUNT" -lt 2 ]; then
    echo "        [fail] expected at least 2 blobs, got $BLOB_COUNT"
    rm -rf "$TMPDIR_TEST"
    exit 1
fi
echo "        [ok] OCI image created with index.json, oci-layout, and $BLOB_COUNT blobs"
rm -rf "$TMPDIR_TEST"
echo "All tests passed"
