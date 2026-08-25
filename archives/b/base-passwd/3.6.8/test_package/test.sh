#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for update-passwd binary
set -eu
UPDATE_PASSWD="$1"
echo "Testing: $UPDATE_PASSWD --version"
"$UPDATE_PASSWD" --version
echo "PASS: update-passwd smoke test passed"
