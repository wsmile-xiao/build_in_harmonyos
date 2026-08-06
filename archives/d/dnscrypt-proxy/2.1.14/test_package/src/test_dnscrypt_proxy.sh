#!/bin/sh
# test_package/src/test_dnscrypt_proxy.sh
#
# L1/L2 smoke test for the dnscrypt-proxy application package (shell wrapper).
#
# This test exercises the actual installed `dnscrypt-proxy` binary by running
# it with the `--version` flag. The binary's --version handler prints the
# AppVersion constant baked in at link time via
# `-ldflags -X main.AppVersion=2.1.14`, so a successful run proves:
#   1. The Go binary was cross-compiled correctly (R34 substantive test).
#   2. The PIE (ET_DYN) binary is loadable on HarmonyOS HMDFS.
#   3. The conanfile.py package() step installed the binary to bin/.
#
# Usage:
#   DNSCRYPT_PROXY_BIN=/path/to/dnscrypt-proxy sh test_dnscrypt_proxy.sh
#   sh test_dnscrypt_proxy.sh          # looks up dnscrypt-proxy on PATH
#
# Exit codes:
#   0 — dnscrypt-proxy --version printed a string containing the expected version
#   1 — dnscrypt-proxy not found, version mismatch, or placeholder binary detected
#   2 — dnscrypt-proxy --version exited non-zero
set -eu

BIN="${DNSCRYPT_PROXY_BIN:-}"
if [ -z "$BIN" ]; then
    if command -v dnscrypt-proxy >/dev/null 2>&1; then
        BIN="$(command -v dnscrypt-proxy)"
    else
        echo "FAIL: dnscrypt-proxy binary not found (set DNSCRYPT_PROXY_BIN or add to PATH)" >&2
        exit 1
    fi
fi

EXPECTED_VERSION="2.1.14"
rc=0
out="$("$BIN" --version 2>&1)" || rc=$?

if [ "$rc" -ne 0 ]; then
    echo "FAIL: dnscrypt-proxy --version exited with $rc" >&2
    echo "output: $out" >&2
    exit 2
fi

case "$out" in
    *"[PLACEHOLDER]"*)
        # R9: conanfile.py builds a C placeholder when the Go toolchain is
        # unavailable; a placeholder must never pass as a genuine build.
        echo "FAIL: dnscrypt-proxy --version output contains placeholder marker (R9)" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac

case "$out" in
    *"$EXPECTED_VERSION"*)
        echo "PASS: dnscrypt-proxy --version output contains $EXPECTED_VERSION"
        exit 0
        ;;
    *)
        echo "FAIL: dnscrypt-proxy --version output does not contain $EXPECTED_VERSION" >&2
        echo "output: $out" >&2
        exit 1
        ;;
esac
