# bird2 — BIRD Internet Routing Daemon

BIRD is a dynamic IP routing daemon supporting BGP, OSPF, RIP, Babel, BFD and other routing protocols. Designed for Linux and UNIX-like systems.

- **Homepage**: https://bird.network.cz/
- **License**: GPL-2.0-or-later
- **Category**: networking

## Available Versions

| Version | Status | Conan Verify | Date |
|---------|--------|--------------|------|
| 2.17.4  | built  | PASS         | 2026-07-06 |

## OHOS Platform Adaptations (2.17.4)

- **E007**: config.guess/config.sub replaced with OHOS-aware versions
- **E091**: `-D__MUSL__` added to resolve sockaddr_storage redefinition conflict
- **HMDFS**: configure `umask 077` → `umask 022` for permission compatibility
- **ncurses**: `--disable-client` (ncurses headers unavailable on OHOS)
- **sysroot**: OHOS SDK sysroot include paths for Linux UAPI kernel headers

## Binaries

- `bird` — BIRD routing daemon (ELF 64-bit aarch64, musl libc)
- `birdcl` — BIRD control client (ELF 64-bit aarch64, musl libc)
