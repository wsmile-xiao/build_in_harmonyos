#!/bin/sh
set -eu

openssl_bin=${1:-openssl}
expected_digest=ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad

version_output=$("$openssl_bin" version -a)
case "$version_output" in
    *"OpenSSL 4.0.1"*) ;;
    *)
        printf '%s\n' "unexpected OpenSSL version" >&2
        exit 1
        ;;
esac

# OpenSSL 4.0 removed engines, so only OPENSSLDIR and MODULESDIR are
# embedded in the CLI. ENGINESDIR no longer exists in the 4.x series.
printf '%s\n' "$version_output" | grep -Fqx 'OPENSSLDIR: "/ssl"'
printf '%s\n' "$version_output" | grep -Fqx 'MODULESDIR: "/lib/ossl-modules"'

digest_output=$(printf 'abc' | "$openssl_bin" dgst -sha256)
case "$digest_output" in
    *"$expected_digest"*) ;;
    *)
        printf '%s\n' "unexpected SHA-256 digest: $digest_output" >&2
        exit 1
        ;;
esac

random_hex=$("$openssl_bin" rand -hex 16)
case "$random_hex" in
    ''|*[!0-9a-f]*)
        printf '%s\n' "unexpected random output: $random_hex" >&2
        exit 1
        ;;
esac
if [ "${#random_hex}" -ne 32 ]; then
    printf '%s\n' "unexpected random output length: ${#random_hex}" >&2
    exit 1
fi

printf '%s\n' "OpenSSL CLI version, path, SHA-256, and random checks passed"
