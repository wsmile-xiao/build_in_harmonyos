# ktls-utils

ktls-utils provides `tlshd`, a user-space TLS handshake agent that services
in-kernel TLS (kTLS) handshake requests on behalf of kernel consumers. It
performs the TLS handshake in userspace with GnuTLS, then programs the
negotiated session keys into the socket via the kTLS `SOL_TLS` setsockopt and
the kernel keyring, so subsequent records are encrypted/decrypted by the kernel.

## Versions

| Version | Status |
| --- | --- |
| 1.4.0 | built |

Homepage: https://github.com/oracle/ktls-utils

Usage (after `conan install`): `tlshd --version`; run the daemon as `tlshd -s`
on a host whose kernel exposes the `handshake` generic-netlink family.

Platform note: the packaged userspace binary builds, links and runs on OHOS
aarch64. Its actual handshake-offload service loop depends on a Linux >= 6.5
kernel built with `CONFIG_TLS` + `CONFIG_KEYS` + `CONFIG_KEYS_REQUEST_CACHE`;
the HongMeng kernel does not register that net family, so the daemon's kernel
dispatch is not exercised here (see `1.4.0/notes.md`).
