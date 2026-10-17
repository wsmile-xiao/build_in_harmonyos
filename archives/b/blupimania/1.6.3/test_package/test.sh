#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for the blupimania executable.
# Runs in conanrun env (PATH/LD_LIBRARY_PATH include the installed package).
set -eu

echo "[test] blupimania --version"
out=$(blupimania --version)
echo "[test] version output: ${out}"
case "${out}" in
  *1.6.3*) echo "[ok] --version reports 1.6.3" ;;
  *) echo "[fail] unexpected version output"; exit 1 ;;
esac
