# yojimbo

networkprotocol's yojimbo for HarmonyOS PC: a secure client/server UDP
protocol library for games, built on netcode.io (connect token handshake +
encrypted packet protocol) and reliable.io (message fragmentation /
reassembly / acks), with a minimal vendored libsodium providing the AEAD
crypto. 1.13.5 is the first adapted release.

The package keeps upstream's fully-vendored self-contained shape: sodium,
netcode, reliable and tlsf objects are folded into the single
`libyojimbo.a`, and serialize is header-only — the package carries zero
registry dependencies. The OHOS (musl) POSIX path needs no source patches:
the platform gates fall through to `*_PLATFORM_UNIX` and little-endian is
detected via `__aarch64__`; the QUIC-family musl traps
(`pthread_setaffinity_np`, `CMSG_NXTHDR` sign-compare) have no call sites
in this tree.
