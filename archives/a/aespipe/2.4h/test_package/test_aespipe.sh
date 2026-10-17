#!/bin/sh
set -eu

aespipe=$1
tmp=${TMPDIR:-/tmp}/aespipe-test-$$
mkdir -p "$tmp"
trap 'rm -rf "$tmp"' EXIT HUP INT TERM

key='correct horse battery staple'
wrong='incorrect password value'
printf '%s\n' "$key" >"$tmp/key"
printf '%s\n' "$wrong" >"$tmp/wrong"
: >"$tmp/plain"
i=0
while [ "$i" -lt 64 ]; do
    printf '0123456789abcdef' >>"$tmp/plain"
    i=$((i + 1))
done

"$aespipe" -p 3 -e AES256 <"$tmp/plain" >"$tmp/encrypted" 3<"$tmp/key"
if cmp -s "$tmp/plain" "$tmp/encrypted"; then
    echo "FAIL: ciphertext is identical to plaintext" >&2
    exit 1
fi
"$aespipe" -d -P "$tmp/key" -e AES256 <"$tmp/encrypted" >"$tmp/decrypted"
cmp -s "$tmp/plain" "$tmp/decrypted"
"$aespipe" -d -P "$tmp/wrong" -e AES256 <"$tmp/encrypted" >"$tmp/wrong-output"
if cmp -s "$tmp/plain" "$tmp/wrong-output"; then
    echo "FAIL: a wrong key reproduced the plaintext" >&2
    exit 1
fi
if "$aespipe" --invalid-option </dev/null >/dev/null 2>&1; then
    echo "FAIL: invalid option was accepted" >&2
    exit 1
fi

echo "PASS: aespipe encryption, decryption, and negative checks"
