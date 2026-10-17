#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke test for acpid 2.0.34 executables
# Runs in conanrun env (PATH includes installed bin/ and sbin/)
set -eu

ACPID_BIN="${ACPID_BIN:-acpid}"
LISTEN_BIN="${LISTEN_BIN:-acpi_listen}"

echo "[test] $ACPID_BIN --version"
"$ACPID_BIN" --version && echo "✅ acpid --version OK" || {
    echo "❌ acpid --version failed"
    exit 1
}

echo "[test] $LISTEN_BIN --help"
"$LISTEN_BIN" --help > /dev/null 2>&1 && echo "✅ acpi_listen --help OK" || {
    echo "❌ acpi_listen --help failed"
    exit 1
}

echo "[test] all acpid executable checks PASSED"
