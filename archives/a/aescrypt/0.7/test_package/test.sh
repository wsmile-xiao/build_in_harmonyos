#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for aescrypt executable
# aescrypt has no --version flag; running without arguments shows usage
set -euo pipefail

echo "[step] aescrypt smoke test"
# aescrypt exits non-zero when run without args, so disable pipefail temporarily
set +o pipefail
output=$(aescrypt 2>&1 || true)
set -o pipefail
echo "$output" | grep -q "Usage" && echo "        [ok] aescrypt usage message" || {
    echo "        [fail] aescrypt did not show usage"
    exit 1
}

set +o pipefail
output=$(aesget 2>&1 || true)
set -o pipefail
echo "$output" | grep -q "Usage" && echo "        [ok] aesget usage message" || {
    echo "        [fail] aesget did not show usage"
    exit 1
}
