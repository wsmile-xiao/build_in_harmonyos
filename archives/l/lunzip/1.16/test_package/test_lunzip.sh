#!/bin/sh
# test_lunzip.sh — lunzip decompression roundtrip + stdout + integrity test.
# Called by test_package/conanfile.py test() method.
#
# Args (passed by conanfile.py):
#   $1  test.txt.lz   — the .lz fixture, restored from res/test.txt.lz.b64
#                        into the test build folder by the conanfile (Python
#                        stdlib base64), never present in the source tree.
#   $2  test.txt      — the upstream plaintext fixture (res/test.txt).
#   $3  work dir      — scratch dir for out_file.txt / out_stdout.txt.
#
# The plaintext fixture (res/test.txt) is the upstream test resource shipped
# in lunzip-1.16/testsuite/ — fixed and auditable, no host lzip required
# (requirement: no target-runtime-unrelated deps to build .lz). Only POSIX
# tools used by the upstream check.sh itself are used here (lunzip, cmp), so
# the test runs on the OHOS target without extra deps.
set -eu

lz_path="${1:-}"
txt_path="${2:-}"
work_dir="${3:-}"

[ -n "${lz_path}" ]  || { echo "FAIL: missing arg1 (.lz path)"; exit 1; }
[ -n "${txt_path}" ] || { echo "FAIL: missing arg2 (.txt path)"; exit 1; }
[ -n "${work_dir}" ] || { echo "FAIL: missing arg3 (work dir)"; exit 1; }

# Sanity: fixtures must exist.
[ -f "${lz_path}" ]  || { echo "FAIL: fixture ${lz_path} missing"; exit 1; }
[ -f "${txt_path}" ] || { echo "FAIL: fixture ${txt_path} missing"; exit 1; }

out_file="${work_dir}/out_file.txt"
out_stdout="${work_dir}/out_stdout.txt"
rm -f "${out_file}" "${out_stdout}"

# Test 1: file decompression — lunzip -d writes out_file, must equal test.txt.
lunzip -dk -o "${out_file}" "${lz_path}" \
  || { echo "FAIL: lunzip -d failed"; exit 1; }
[ -f "${out_file}" ] || { echo "FAIL: decompressed file not created"; exit 1; }
cmp -s "${txt_path}" "${out_file}" \
  || { echo "FAIL: file decompress content mismatch"; exit 1; }
echo "PASS: file decompression matches plaintext exactly"

# Test 2: stdout decompression — lunzip -cd writes to stdout, must equal test.txt.
lunzip -cd "${lz_path}" > "${out_stdout}" \
  || { echo "FAIL: lunzip -cd failed"; exit 1; }
cmp -s "${txt_path}" "${out_stdout}" \
  || { echo "FAIL: stdout decompress content mismatch"; exit 1; }
echo "PASS: stdout decompression matches plaintext exactly"

# Test 3: integrity test — lunzip -t must succeed (exit 0) on a valid .lz.
lunzip -t "${lz_path}" \
  || { echo "FAIL: lunzip -t failed"; exit 1; }
echo "PASS: integrity test (-t) succeeded"

rm -f "${out_file}" "${out_stdout}"
