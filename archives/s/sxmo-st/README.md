# sxmo-st — Sxmo Terminal Emulator

**Package**: sxmo-st
**Version**: 0.8.4.1
**Upstream**: https://git.sr.ht/~mil/sxmo-st
**License**: MIT
**Build System**: POSIX Makefile
**Type**: Application (CLI tool)

## Description

sxmo-st is a fork of the suckless `st` terminal emulator adapted for the SXMO
(Simple X Mobile) Linux mobile environment. It is a lightweight X11 terminal
emulator that uses Xft for font rendering and fontconfig/freetype2 for font
discovery.

## Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| libx11 | 1.8.13 | X11 client protocol |
| libxft | 2.3.9 | X FreeType font rendering |
| fontconfig | 2.18.3 | Font discovery and matching |
| freetype | 2.14.3 | Font rendering engine |
| xorgproto | 2025.1 | X11 protocol headers (Xatom.h, keysym.h, extensions/render.h) |
| libxrender | 0.9.12 | X Render extension (X11/extensions/Xrender.h) |
| pkgconf | 3.0.6 (tool) | pkg-config for build |

## OHOS Adaptation

On HarmonyOS, the X11 client libraries are provided by the OHOS-ported
libx11/libxft/fontconfig/freetype recipes. The `st` binary cannot execute
on OHOS (no X11 display server), but the build produces a functional CLI
tool that links against the OHOS X11 client stack.

### Build Patches

- `config.mk` is rewritten to inject conan dependency include/lib paths.
- pkg-config is used to resolve fontconfig and freetype2 flags.

### Upstream Tests

Upstream has no automated tests (no test directory, no test targets).

### OHOS Consumer Test

A consumer test (`ohos_x11_consumer.c`) verifies that the X11/Xft/fontconfig
libraries can be consumed by a downstream application. It exercises real
API calls to verify the OHOS-adapted client libraries work correctly.

## Build Verification

- [x] conan create
- [x] conan-verify (G1-G4)
- [x] W3 local CI
- [x] W2 structure check
- [ ] W4 pre-PR audit
- [ ] CI pipeline
