#!/data/service/hnp/bin/bash
# test_package/test.sh — R34 consumer test for the packaged `zst` CLI.
# Executed by test_package/conanfile.py inside the conanrun environment,
# so the installed binary is on PATH.
set -euo pipefail

echo "[test] zst on PATH: $(command -v zst)"

# scratch dir outside the recipe tree: conan runs test_package with the recipe's
# test_package/ as build folder, so writing there would litter the archive
work="${TMPDIR:-/tmp}/zst-test-$$"
trap 'rm -rf "$work"' EXIT
rm -rf "$work"
mkdir -p "$work"
cd "$work"

printf 'zst round-trip payload\nline %s\n' 1 2 3 4 5 6 7 8 > payload.txt
cp payload.txt expected.txt

rc=0
for pair in "zstd:.zst" "xz:.xz" "gzip:.gz" "bzip2:.bz2"; do
    tool="${pair%%:*}"
    ext="${pair##*:}"
    echo "[test] round-trip via ${tool} (${ext})"

    rm -f "payload.txt${ext}"
    zst -F"${tool}" payload.txt
    if [ ! -f "payload.txt${ext}" ]; then
        echo "FAIL: ${tool} produced no payload.txt${ext}"
        rc=1
        continue
    fi

    # integrity check on the produced archive
    zst -t "payload.txt${ext}"

    rm -f payload.txt
    zst -d "payload.txt${ext}"
    if cmp expected.txt payload.txt; then
        echo "OK: ${tool} round-trip byte-identical"
    else
        echo "FAIL: ${tool} round-trip mismatch"
        rc=1
    fi
    cp expected.txt payload.txt
done

echo "[test] unknown format must be rejected"
if zst -Fnosuchfmt payload.txt >/dev/null 2>&1; then
    echo "FAIL: unknown format accepted"
    rc=1
else
    echo "OK: unknown format rejected"
fi

[ "$rc" -eq 0 ] || exit 1
echo "[test] all zst consumer checks passed"
