# xf86-video-fbdev 0.5.1 - Build Notes

## Overview
X.Org framebuffer device video driver. Provides display output via Linux framebuffer devices (/dev/fb*).

## Build Configuration
- **Compiler**: clang 15.0.4 (OHOS SDK)
- **Target**: OpenHarmony aarch64
- **Prefix**: /storage/Users/currentUser/usr/local
- **Build approach**: Direct compilation (bypass autotools due to missing configure script)

## Build Issues and Solutions

### 1. Missing xorg-server Conan package
xorg-server is not available as a Conan package in the artifact repo. Solution: download
xorg-server 21.1.15 source and install SDK headers manually in the conanfile.py build() step.

### 2. Removed old PCI API (xorg-server 21.x)
The old PCI functions (xf86ParsePciBusString, xf86CheckPciSlot, xf86ClaimPciSlot, etc.)
were removed from xorg-server 21.x. The xf86-video-fbdev 0.5.1 code uses these in
`#ifndef XSERVER_LIBPCIACCESS` blocks. Solution: define XSERVER_LIBPCIACCESS to skip
the old code path.

### 3. Missing pciaccess.h
When XSERVER_LIBPCIACCESS is defined, the code includes <pciaccess.h>. Solution:
download libpciaccess 0.18 source and install the header.

### 4. Missing automake
The GitLab archive source has no pre-generated configure script (no automake on build
machine). Solution: compile fbdev.c directly into fbdev_drv.so, bypassing autotools.

### 5. HMDFS umask issue
config.status uses umask 077 which creates directories with restricted permissions on
HMDFS. Fixed by patching config.status to use umask 022.

### 6. config.h generation
The source expects a config.h from configure. Created manually with PACKAGE and
PACKAGE_VERSION defines.

## Installed Files
- lib/xorg/modules/drivers/fbdev_drv.so (39KB, AArch64 ELF shared object)
- share/man/man4/fbdev.4

## Dependencies
- xorg-server >= 21.1.15 (SDK headers, from source)
- pixman >= 0.46.4 (from Conan)
- xorgproto/2025.1 (from Conan)
- libpciaccess 0.18 (header only, from source)
