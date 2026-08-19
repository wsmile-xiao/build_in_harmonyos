#!/data/service/hnp/bin/bash
# test_package/test.sh — smoke + functional test for the enchive executable
# Runs in conanrun env (PATH includes the installed bin/).
# R34: genuinely exercises the packaged binary — keygen + encrypt + decrypt
# round-trip, verifying that the crypto functions work correctly.
set -euo pipefail

echo "[test] enchive smoke test (--version)"
enchive --version
if ! enchive --version 2>&1 | grep -q "3.5"; then
    echo "FAIL: enchive --version did not output 3.5"
    exit 1
fi
echo "   OK: version matches"

echo "[test] enchive keygen + encrypt + decrypt round-trip"
WORKDIR=$(mktemp -d "${TMPDIR:-/data/service/hnp/tmp}/enchive-test.XXXXXX")
trap 'rm -rf "$WORKDIR"' EXIT
cd "$WORKDIR"

# Generate keypair with empty passphrase (non-interactive)
printf '\n' | enchive -p pubkey -s seckey keygen 2>&1 || {
    echo "FAIL: keygen failed"
    exit 1
}

if [ ! -f pubkey ] || [ ! -f seckey ]; then
    echo "FAIL: keygen did not produce key files"
    exit 1
fi
echo "   OK: keypair generated (pub=$(wc -c < pubkey)B, sec=$(wc -c < seckey)B)"

# Create test plaintext
echo "Hello enchive on OHOS!" > plaintext.txt

# Encrypt (archive) with public key
printf '\n' | enchive -p pubkey -s seckey archive plaintext.txt 2>&1 || {
    echo "FAIL: archive (encrypt) failed"
    exit 1
}

if [ ! -f plaintext.txt.enchive ]; then
    echo "FAIL: archive did not produce encrypted file"
    exit 1
fi
echo "   OK: encrypted ($(wc -c < plaintext.txt.enchive)B)"

# Decrypt (extract) back to a file
printf '\n' | enchive -p pubkey -s seckey extract plaintext.txt.enchive decrypted.txt 2>&1 || {
    echo "FAIL: extract (decrypt) failed"
    exit 1
}

if [ ! -f decrypted.txt ]; then
    echo "FAIL: extract did not produce decrypted file"
    exit 1
fi

# Verify round-trip integrity
if diff -q plaintext.txt decrypted.txt >/dev/null 2>&1; then
    echo "   OK: round-trip decrypt matches original"
else
    echo "FAIL: decrypted content does not match original"
    exit 1
fi

echo "[test] enchive fingerprint"
printf '\n' | enchive -p pubkey -s seckey fingerprint 2>&1 | grep -qE '^[0-9a-f]{8}(-[0-9a-f]{8}){3}$' || {
    echo "FAIL: fingerprint format unexpected"
    exit 1
}
echo "   OK: fingerprint valid"

echo "ALL TESTS PASSED"
