#!/data/service/hnp/bin/bash
set -euo pipefail

unit_dir="${TMPDIR:-$PWD}/bochs-bximage-unit-$$"
image="$unit_dir/disk.img"
trap 'rm -rf "$unit_dir"' EXIT
rm -rf "$unit_dir"
mkdir -p "$unit_dir"

echo "[step] bximage option parser"
set +e
help_output="$(bximage --help 2>&1)"
help_status=$?
invalid_output="$(bximage -q -func=unsupported "$image" 2>&1)"
invalid_status=$?
set -e

test "$help_status" -lt 126
grep -Fq -- "-func=..." <<<"$help_output"
grep -Fq -- "-sectsize=..." <<<"$help_output"
test "$invalid_status" -ne 0
grep -Fq "Unknown bximage mode 'unsupported'" <<<"$invalid_output"

echo "[step] bximage flat-image creation"
create_output="$(
  bximage -q -func=create -hd=10M -imgmode=flat -sectsize=512 "$image" 2>&1
)"
test -f "$image"
image_size="$(wc -c <"$image" | tr -d '[:space:]')"
expected_size=$((
  (10 * 1024 * 1024 / (16 * 63 * 512)) * 16 * 63 * 512
))
test "$image_size" -eq "$expected_size"
grep -Fq 'mode=flat' <<<"$create_output"

echo "[step] bximage image metadata"
info_output="$(bximage -q -func=info "$image" 2>&1)"
grep -Fq "disk image mode = 'flat'" <<<"$info_output"
grep -Fq "geometry = 20/16/63" <<<"$info_output"

echo "        [ok] bximage command unit tests passed"
