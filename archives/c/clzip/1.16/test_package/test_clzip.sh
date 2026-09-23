#!/bin/sh
# test_clzip.sh — clzip decompression, integrity and compression roundtrip test.
# Called by test_package/conanfile.py test() method.
#
# Args (passed by conanfile.py):
#   $1  test.txt.lz   — the .lz fixture, restored from res/test.txt.lz.b64
#                       into a private temp dir by the conanfile (Python
#                       stdlib base64), never present in the source tree.
#   $2  test.txt      — the upstream plaintext fixture (res/test.txt).
#   $3  work dir      — scratch dir for decompressed/roundtrip outputs.
#
# The fixtures are the upstream test resources shipped in
# clzip-1.16/testsuite/ — fixed and auditable. Only POSIX tools used by the
# upstream check.sh itself are used here (clzip, cmp), so the test runs on
# the OHOS target without extra deps.
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
roundtrip="${work_dir}/roundtrip.txt"
rm -f "${out_file}" "${out_stdout}" "${roundtrip}"

# Test 1: file decompression — clzip -d writes out_file, must equal test.txt.
cp "${lz_path}" "${work_dir}/in.lz"
clzip -dq "${work_dir}/in.lz" \
  || { echo "FAIL: clzip -d failed"; exit 1; }
[ -f "${work_dir}/in" ] || { echo "FAIL: decompressed file not created"; exit 1; }
cmp -s "${txt_path}" "${work_dir}/in" \
  || { echo "FAIL: file decompress content mismatch"; exit 1; }
echo "PASS: file decompression matches plaintext exactly"

# Test 2: stdout decompression — clzip -cd writes to stdout, must equal test.txt.
clzip -cd "${lz_path}" > "${out_stdout}" \
  || { echo "FAIL: clzip -cd failed"; exit 1; }
cmp -s "${txt_path}" "${out_stdout}" \
  || { echo "FAIL: stdout decompress content mismatch"; exit 1; }
echo "PASS: stdout decompression matches plaintext exactly"

# Test 3: integrity test — clzip -t must succeed (exit 0) on a valid .lz.
clzip -t "${lz_path}" \
  || { echo "FAIL: clzip -t failed"; exit 1; }
echo "PASS: integrity test (-t) succeeded"

# Test 4: compression roundtrip — clzip compresses the plaintext fixture,
# then decompresses its own .lz output back, byte-compare against the source.
cp "${txt_path}" "${work_dir}/data"
clzip -k -f -q "${work_dir}/data" \
  || { echo "FAIL: clzip compress failed"; exit 1; }
[ -f "${work_dir}/data.lz" ] || { echo "FAIL: no .lz produced"; exit 1; }
clzip -dk -f -q -o "${roundtrip}" "${work_dir}/data.lz" \
  || { echo "FAIL: clzip roundtrip decompress failed"; exit 1; }
cmp -s "${txt_path}" "${roundtrip}" \
  || { echo "FAIL: compression roundtrip mismatch"; exit 1; }
echo "PASS: compression roundtrip is byte-exact"

rm -f "${out_file}" "${out_stdout}" "${roundtrip}"
echo "clzip consumer test: all 4 checks passed"
