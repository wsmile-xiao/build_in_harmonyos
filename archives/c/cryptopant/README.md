# cryptopant

CryptopANT is a C library for IP address anonymization using the crypto-PAn algorithm (prefix-preserving).

- Supports IPv4, IPv6 and MAC address anonymization / de-anonymization (with key).
- Provides `scramble_ips` sample utility.

OHOS adaptation builds the library with OpenSSL 3.x (AES/Blowfish/SHA1/MD5 backends) and runs the upstream `make check` suite (16 checks).

- Upstream: https://ant.isi.edu/software/cryptopANT/
- License: GPL-2.0-only
