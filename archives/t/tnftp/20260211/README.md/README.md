# tnftp 20260211 for OpenHarmony (aarch64-unknown-linux-ohos)

## Overview

tnftp is the NetBSD FTP client, a portable version of the FTP client from NetBSD.
This package provides a pre-compiled binary for OpenHarmony (HarmonyOS) on aarch64.

## Build Information

- **Version**: 20260211
- **Build System**: autotools
- **Compiler**: clang 15.0.4 (OpenHarmony toolchain)
- **Target**: aarch64-unknown-linux-ohos
- **Configure Options**: `--enable-ssl --enable-ipv6`
- **Status**: published

## Dependencies

- libedit 3.1 (line editing library)
- ncurses 6.5 (terminal handling)
- openssl 3.x (SSL/TLS support)

## Patches Applied

1. **0001-Makefile.in.patch** — Add getpass to LIBOBJS/LTLIBOBJS (OHOS lacks getpass())
2. **0002-libnetbsd-Makefile.in.patch** — Add getpass to libnetbsd LIBOBJS/LTLIBOBJS
3. **0003-libnetbsd-getpass.c.patch** — Provide getpass() replacement for musl/OHOS
4. **0004-buildaux-config.guess.patch** — Update config.guess to recognize aarch64-unknown-linux-ohos
5. **0005-buildaux-config.sub.patch** — Update config.sub to accept aarch64-unknown-linux-ohos

## Key Adaptation Notes

- OHOS/musl libc does not provide `getpass()`. A replacement implementation using
  `fgets()` on `/dev/tty` with termios is provided in `libnetbsd/getpass.c`.
- The original `config.guess` (2018-08-29) and `config.sub` (2018-08-29) do not
  recognize HarmonyOS. They are replaced with 2025-07-10 versions from the hints/
  directory that support `aarch64-unknown-linux-ohos`.
- The original configure script is preserved (no autoreconf), because autoreconf-generated
  scripts are incompatible with toybox `/bin/sh` (which is the default shell on OHOS).

## Installation

```bash
# Binary is installed to: /storage/Users/currentUser/usr/local/bin/tnftp
# Man page: /storage/Users/currentUser/usr/local/share/man/man1/tnftp.1
```

## Usage

```bash
tnftp <host>          # Connect to FTP server
tnftp -u <url>        # Fetch file from URL (supports ftp:// and http://)
```

Note: tnftp does not have a `--version` flag.
