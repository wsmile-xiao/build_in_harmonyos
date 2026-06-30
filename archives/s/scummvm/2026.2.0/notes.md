# Build Notes — scummvm 2026.2.0

## Build Date
2026-05-25

## Build System
Custom configure script (not autoconf) + GNU Make

## Build Configuration
```bash
./configure --prefix=/usr/local
```

Configure detected: `aarch64-unknown-linux-ohos` (HarmonyOS target)

## Build Duration
~30 minutes

## Dependencies
| Dependency | Version | Source |
|-----------|---------|--------|
| SDL2 | 2.30.10 | cmd-pkgs |
| FreeType2 | 2.14.3 | cmd-pkgs |
| FriBiDi | 1.0.16 | cmd-pkgs |
| libjpeg-turbo | 3.1.0 | cmd-pkgs |
| libpng | 1.6.44 | cmd-pkgs |
| zlib | 1.2.13 | system |

## Key Issues & Resolutions

### 1. HarmonyOS platform not recognized by config.guess
ScummVM's bundled config.guess doesn't detect HarmonyOS.
Resolution: Added HarmonyOS case branch to config.guess mapping UNAME_MACHINE to aarch64/x86_64/arm/i686 and producing `*-unknown-linux-ohos`.

### 2. HarmonyOS not recognized by config.sub
ScummVM's bundled config.sub doesn't accept `linux-ohos` as a valid OS.
Resolution: Added `ohos-linux` pattern to config.sub's OS detection and `ohos*` to the recognized system type patterns.

## Build Output
- scummvm (executable) — SDL2 backend with OpenGL shaders

## Enabled Features
- SDL2 backend, OpenGL (with shaders), FreeType2, FriBiDi
- JPEG, PNG, zlib, ENet, TiMidity, SEQ MIDI
- MT32EMU, BINK, RGB color, HQ/Edge scalers
- 80+ game engine plugins (all as STATIC_PLUGIN)
- Translation, language detection, IMGUI debugger

## Disabled Features
- OGG/Vorbis/Tremor (no codec packages)
- FLAC, MAD, A52, FluidSynth (no packages)
- ALSA, sndio (not available on HarmonyOS)
- Discord, Cloud, NASM, GTK (not relevant)
- Dynamic module loading (STATIC_PLUGIN only)
- SSE2/AVX2 (NEON used instead for aarch64)

## Verify
```bash
scummvm --version
# Output: ScummVM 2026.2.0 (May 25 2026 23:32:44)
# Features compiled in: SEQ TiMidity RGB zLib FreeType2 FriBiDi JPEG PNG ENet SDL2 TinyGL OpenGL (with shaders)
```

---
**编译结束**: 2026-05-25 23:32
**最终状态**: built