# xf86-video-dummy

X.Org dummy video driver. Creates a virtual framebuffer with no physical output.
Useful for headless X server testing and development.

## Version
0.4.1

## Build
- Build system: autotools (source) / direct compilation (conan recipe)
- Compiler: clang 15.0.4 (OHOS SDK)
- Target: OpenHarmony aarch64

## Dependencies
- xorgproto/2025.1 (conan)
- pixman/0.46.4 (conan)
- xorg-server 21.1.15 SDK headers (downloaded at build time)

## Install Path
- lib/xorg/modules/drivers/dummy_drv.so
