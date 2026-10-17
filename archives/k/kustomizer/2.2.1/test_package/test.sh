#!/data/service/hnp/bin/bash
# test_package/test.sh - functional smoke test for the kustomizer executable.
# Runs under the conanrun environment (PATH includes the package bin/).
# It really invokes the binary, including an offline manifest build, so this
# is not an empty/print-only test (R34).
set -euo pipefail

cd "$(dirname "$0")"

fail() {
    echo "[FAIL] $*"
    exit 1
}

echo "[1/3] kustomizer --version"
version_out="$(kustomizer --version)"
echo "$version_out"
echo "$version_out" | grep -q "kustomizer version 2.2.1" \
    || fail "--version output does not contain 'kustomizer version 2.2.1'"

echo "[2/3] kustomizer --help"
help_out="$(kustomizer --help)"
echo "$help_out" | grep -q "Available Commands" \
    || fail "--help output missing command list"
echo "$help_out" | grep -Eq "push|pull|build" \
    || fail "--help output missing expected subcommands"

echo "[3/3] offline: kustomizer build inventory -f testdata/cm.yaml"
build_out="$(kustomizer build inventory smoke-app -n smoke-ns -f testdata/cm.yaml)"
echo "$build_out"
echo "$build_out" | grep -q "kind: ConfigMap" \
    || fail "offline build output missing ConfigMap"
echo "$build_out" | grep -q "name: smoke-config" \
    || fail "offline build output missing the manifest name"
echo "$build_out" | grep -q "key: value" \
    || fail "offline build output missing the ConfigMap data"

echo "[PASS] all kustomizer test_package checks succeeded"
