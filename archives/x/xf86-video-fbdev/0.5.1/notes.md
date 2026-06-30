# xf86-video-fbdev 0.5.1 - Build Notes

## Overview
X.Org framebuffer device video driver. Used for displaying on Linux framebuffer devices.

## Build Configuration
- **Compiler**: clang 15.0.4 (OHOS SDK) + GNU ld.bfd (binutils 2.45)
- **Target**: OpenHarmony aarch64
- **Prefix**: /storage/Users/currentUser/usr/local

## Build Issues and Solutions
Same as xf86-video-dummy:
- HMDFS umask fix applied to config.status
- CC wrapper for ELF signing
- xorg-server SDK headers from multiple subdirectories

## Installed Files
- lib/xorg/modules/drivers/fbdev_drv.so (ELF-signed)
- share/man/man4/fbdev.4
