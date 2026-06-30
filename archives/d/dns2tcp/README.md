# dns2tcp

dns2tcp is a tool for relaying TCP connections over DNS (DNS tunnel). It includes both a client (dns2tcpc) and a server (dns2tcpd) component.

## Version 0.5.2

- **Status**: published
- **Build system**: autotools
- **Compiler**: clang
- **Date**: 2026-06-15

## Patches

5 patches applied:
1. `0001-common-dns.c.patch` - extern int debug definition for OHOS (#ifdef __OHOS__)
2. `0002-common-includes-debug.h.patch` - extern int debug declaration for OHOS
3. `0003-config.guess.patch` - Replace with automake-1.17 version (HarmonyOS + aarch64)
4. `0004-config.sub.patch` - Replace with automake-1.17 version (HarmonyOS + aarch64)
5. `0005-configure.patch` - umask 077→022 (E011 HMDFS fix)

## Binaries

- `dns2tcpd` - DNS tunnel server
- `dns2tcpc` - DNS tunnel client (outputs version: dns2tcp v0.5.2)
