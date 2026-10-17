#!/bin/sh
set -eu

file_bin=$1
work_dir=$2
runner=${3-}
fixture="$work_dir/file-formula-fixture.txt"

run_file() {
  if [ -n "$runner" ]; then
    "$runner" "$file_bin" "$@"
  else
    "$file_bin" "$@"
  fi
}

mkdir -p "$work_dir"
printf '%s\n' 'OpenHarmony file-formula consumer test' > "$fixture"

version=$(run_file --version)
case "$version" in
  *file-5.48*) ;;
  *)
    echo "FAIL: unexpected version output: $version" >&2
    exit 1
    ;;
esac

mime=$(run_file --brief --mime-type "$fixture")
if [ "$mime" != "text/plain" ]; then
  echo "FAIL: expected text/plain, got $mime" >&2
  exit 1
fi

encoding=$(run_file --brief --mime-encoding "$fixture")
if [ "$encoding" != "us-ascii" ]; then
  echo "FAIL: expected us-ascii, got $encoding" >&2
  exit 1
fi

description=$(run_file --brief "$fixture")
case "$description" in
  *ASCII*text*) ;;
  *)
    echo "FAIL: expected an ASCII text description, got $description" >&2
    exit 1
    ;;
esac

echo "file-formula 5.48 consumer test: PASS"
