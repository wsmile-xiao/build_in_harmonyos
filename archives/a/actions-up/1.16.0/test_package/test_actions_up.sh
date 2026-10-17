#!/system/bin/sh
set -eu

echo "[test 1] actions-up exists"
command -v actions-up >/dev/null

echo "[test 2] version"
VERSION=$(actions-up --version)
echo "$VERSION"
echo "$VERSION" | grep -q "actions-up/1.16.0"

echo "[test 3] help"
HELP=$(actions-up --help)
echo "$HELP"
echo "$HELP" | grep -q "Usage:"

echo "All 3 tests passed."
