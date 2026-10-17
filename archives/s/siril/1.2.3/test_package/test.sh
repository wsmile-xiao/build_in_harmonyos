#!/data/service/hnp/bin/bash
# test_package/test.sh — real consumer test for the siril-cli executable.
#
# R34: test_package sources must genuinely exercise the packaged product.
# This script executes the packaged siril-cli binary and asserts both the
# return code and the version output, so it fails if the binary is missing,
# broken, or not runnable on the OHOS target.
#
# Usage: test.sh [path-to-siril-cli]
#   The path defaults to "siril-cli" (resolved via PATH from the conanrun
#   environment); conanfile.py test() passes the absolute package path.
set -eu

SIRIL_CLI="${1:-siril-cli}"

echo "[test] running: $SIRIL_CLI --version"
OUTPUT=$("$SIRIL_CLI" --version 2>&1) || {
    echo "FAIL: siril-cli --version exited non-zero (missing/broken binary)"
    exit 1
}
echo "$OUTPUT"

case "$OUTPUT" in
    *"siril 1.2.3"*)
        echo "OK: siril-cli --version reports 'siril 1.2.3'"
        ;;
    *)
        echo "FAIL: version output does not contain 'siril 1.2.3'"
        exit 1
        ;;
esac
