# xf86-video-dummy 0.4.1 - Build Notes

## Overview
X.Org dummy video driver. Creates a virtual framebuffer with no physical output.
Useful for headless X server testing and development.

## Build Configuration
- **Compiler**: clang 15.0.4 (OHOS SDK) + GNU ld.bfd (binutils 2.45)
- **Target**: OpenHarmony aarch64
- **Prefix**: /storage/Users/currentUser/usr/local

## Build Issues and Solutions

### 1. HMDFS umask permission issue
config.status uses `umask 077` when creating temp directories. On HMDFS, this creates
directories with restricted permissions (2700) that prevent even the owner from writing.
Fixed by patching config.status to use `umask 022`.

### 2. ELF signing required
Newly-compiled binaries must be ELF-signed to run on OpenHarmony. Used a CC wrapper
script ($HOME/tmp/cc-sign-wrapper.sh) that automatically signs compiled binaries.

### 3. XORG_DRIVER_CHECK_EXT macro missing
The xorg-server.m4 macro file was not installed. Copied from xorg-server source
to $HOME/usr/local/share/aclocal/ for autoreconf to find.

### 4. Missing SDK headers
Required xorg-server SDK headers from multiple subdirectories (render/, randr/,
miext/, mi/, etc.) that were not initially copied. Copied all 227 headers from
xorg-server source.

### 5. pciaccess.h missing
The xorg-server headers include <pciaccess.h> unconditionally. Installed the header
from libpciaccess 0.18 source.

### 6. xorg-server.h missing
Created manually with defines matching xorg-server 21.1.15 configuration:
- XORG_VERSION_CURRENT = 12101015
- RANDR, RENDER, COMPOSITE, XINPUT enabled
- X_BYTE_ORDER = 1234 (little endian)

## Installed Files
- lib/xorg/modules/drivers/dummy_drv.so (39KB, ELF-signed)
---

**编译结束**: 2026-09-17 13:51
**最终状态**: built
