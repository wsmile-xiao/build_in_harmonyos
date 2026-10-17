#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for squashfs-tools-ng tools
# Runs in conanrun env (PATH includes installed bin/)
set -euo pipefail

WORKDIR="${TMPDIR:-$HOME/tmp}/sqfs_test_$$"
cleanup() { rm -rf "$WORKDIR"; }
trap cleanup EXIT

check_version() {
    local tool="$1" out
    echo "[test] $tool --version"
    out="$("$tool" --version 2>&1 | head -1)"
    # upstream format: "rdsquashfs (squashfs-tools-ng) 1.3.2"
    echo "$out" | grep -q "squashfs-tools-ng" || {
        echo "FAIL $tool --version unexpected output: $out"
        exit 1
    }
    echo "PASS $tool --version OK"
}

for tool in rdsquashfs gensquashfs sqfs2tar tar2sqfs sqfsdiff; do
    check_version "$tool"
done

# Round-trip test: create a squashfs image and extract it
mkdir -p "$WORKDIR/src"
echo "hello squashfs-tools-ng" > "$WORKDIR/src/test.txt"

echo "[test] gensquashfs round-trip"
gensquashfs -D "$WORKDIR/src" "$WORKDIR/test.sqfs" 2>&1 || {
    echo "FAIL gensquashfs create failed"
    exit 1
}

echo "[test] rdsquashfs extract"
rdsquashfs -u / -p "$WORKDIR/out" "$WORKDIR/test.sqfs" 2>&1 || {
    echo "FAIL rdsquashfs extract failed"
    exit 1
}

if [ -f "$WORKDIR/out/test.txt" ]; then
    diff "$WORKDIR/src/test.txt" "$WORKDIR/out/test.txt" && echo "PASS round-trip OK" || {
        echo "FAIL round-trip content mismatch"
        exit 1
    }
else
    echo "FAIL extracted file not found"
    exit 1
fi

# tar interop: tar -> sqfs -> tar, compare extracted content
echo "[test] tar2sqfs + sqfs2tar interop"
tar -C "$WORKDIR/src" -cf "$WORKDIR/src.tar" test.txt 2>&1 || {
    echo "FAIL tar create failed"
    exit 1
}
# tar2sqfs reads the tar archive from stdin, writes the image to argv
tar2sqfs "$WORKDIR/src.sqfs" < "$WORKDIR/src.tar" 2>&1 || {
    echo "FAIL tar2sqfs failed"
    exit 1
}
sqfs2tar "$WORKDIR/src.sqfs" > "$WORKDIR/out.tar" 2>&1 || {
    echo "FAIL sqfs2tar failed"
    exit 1
}
mkdir -p "$WORKDIR/tar_out"
tar -C "$WORKDIR/tar_out" -xf "$WORKDIR/out.tar" 2>&1 || {
    echo "FAIL tar extract failed"
    exit 1
}
diff "$WORKDIR/src/test.txt" "$WORKDIR/tar_out/test.txt" && echo "PASS tar interop OK" || {
    echo "FAIL tar interop content mismatch"
    exit 1
}

# sqfsdiff: compare two images built from the same source content
echo "[test] sqfsdiff"
sqfsdiff -a "$WORKDIR/test.sqfs" -b "$WORKDIR/src.sqfs" 2>&1 && echo "PASS sqfsdiff OK" || {
    echo "FAIL sqfsdiff reported differences"
    exit 1
}

echo "All tests passed"
