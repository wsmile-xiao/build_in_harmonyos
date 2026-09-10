#!/usr/bin/env bash
# test_package/test.sh — functional tests for mklittlefs 4.1.0
# Round-trip create/list/unpack with programmatic text and binary
# fixtures, plus a corrupted-image non-zero exit check.
# No network, no pre-built binary fixtures.
set -euo pipefail

WORK=$(mktemp -d "${TMPDIR:-$HOME}/mklittlefs.XXXXXX")
trap 'rm -rf "$WORK"' EXIT

fail() {
    echo "FAIL: $1" >&2
    exit 1
}

IMG="$WORK/test.img"
SIZE=1048576

echo "[1/6] build input tree (multi-level dirs, empty file, text, zero-byte binary)"
mkdir -p "$WORK/in/dir1/sub" "$WORK/in/dir2"
: > "$WORK/in/empty.txt"
printf 'hello mklittlefs\nline two\n' > "$WORK/in/dir1/text.txt"
# binary fixture with embedded NUL bytes, generated programmatically
printf 'B\000I\000N\000\377\376\000abc\000' > "$WORK/in/dir1/sub/blob.bin"
printf 'second file\n' > "$WORK/in/dir2/second.txt"

echo "[2/6] create image"
mklittlefs -c "$WORK/in" -s "${SIZE}" "$IMG" || fail "create failed"

echo "[3/6] list image and verify paths"
# Upstream list output concatenates parent path and name for nested
# entries (dir1/text.txt prints as //dir1text.txt), so assert on the
# exact printed forms observed from the real binary.
LIST=$(mklittlefs -l "$IMG") || fail "list failed"
for p in '/empty.txt' '//dir1text.txt' '//dir1/subblob.bin' '//dir2second.txt'; do
    echo "$LIST" | grep -qF "$p" || fail "list missing path: $p"
done

echo "[4/6] unpack image to a fresh directory"
mkdir -p "$WORK/out"
mklittlefs -u "$WORK/out" -s "${SIZE}" "$IMG" || fail "unpack failed"

echo "[5/6] compare tree structure, sizes, and byte-exact contents"
(cd "$WORK/in" && find . | sort) > "$WORK/in.tree"
(cd "$WORK/out" && find . | sort) > "$WORK/out.tree"
diff "$WORK/in.tree" "$WORK/out.tree" || fail "tree structure differs"
for f in empty.txt dir1/text.txt dir1/sub/blob.bin dir2/second.txt; do
    a=$(wc -c < "$WORK/in/$f")
    b=$(wc -c < "$WORK/out/$f")
    [ "$a" -eq "$b" ] || fail "size mismatch: $f ($a != $b)"
    cmp "$WORK/in/$f" "$WORK/out/$f" || fail "content mismatch: $f"
done

echo "[6/6] corrupted image must exit non-zero"
head -c 4096 "$IMG" > "$WORK/trunc.img"
if mklittlefs -l "$WORK/trunc.img" -s "${SIZE}" >/dev/null 2>&1; then
    fail "corrupted image accepted (exit 0)"
fi

echo "mklittlefs test_package: OK"
