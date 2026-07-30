#!/bin/sh
set -eu

test_root="${TMPDIR:-/tmp}/duc-conan-test"
test_db="${test_root}/duc.db"

rm -rf "${test_root}"
mkdir -p "${test_root}/nested"
printf 'duc test\n' > "${test_root}/file.txt"
printf 'nested test\n' > "${test_root}/nested/file.txt"

export DUC_DATABASE="${test_db}"
duc index "${test_root}"
duc info
duc ls "${test_root}"

rm -rf "${test_root}"
