#!/bin/sh
set -eu

cpio_bin="${CPIO_BIN:-cpio}"
root="$(mktemp -d "${TMPDIR:-/tmp}/cpio-consumer.XXXXXX")"
archive="$root/archive.cpio"
trap 'rm -rf "$root"' EXIT HUP INT TERM
mkdir -p "$root/input/sub" "$root/output"
printf 'cpio consumer payload\n' > "$root/input/hello.txt"
printf 'nested payload\n' > "$root/input/sub/nested.txt"

cd "$root/input"
find . -print | "$cpio_bin" --create --format=newc --file="$archive" >/dev/null
cd "$root/output"
"$cpio_bin" --extract --make-directories --file="$archive" >/dev/null

test "$(cat hello.txt)" = "cpio consumer payload"
test "$(cat sub/nested.txt)" = "nested payload"
test -s "$archive"
echo "cpio archive round-trip: PASS"
