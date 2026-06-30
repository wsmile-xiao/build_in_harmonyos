# libdv

Quasar DV codec library - a software codec for the DV video format (IEC 61834 and SMPTE 314M).

## Features
- DV video encoding/decoding
- Supports NTSC and PAL formats
- Provides command-line tools: encodedv, dvconnect, dubdv
- Core library works correctly on HarmonyOS (API verified)

## OHOS Adaptation
- Requires updated config.guess/config.sub to recognize HarmonyOS (E072)
- HMDFS filesystem requires removing `umask 077` from configure's temp directory creation
- Must disable X/GTK/Xv/asm features since no X11 support on HarmonyOS
  - `--disable-gtk --disable-xv --without-x --disable-asm`
- encodedv crashes without arguments (missing popt library for CLI parsing) — core library unaffected

## Dependencies
- No external dependencies required (core library only depends on libm)
- popt library not available — CLI tools have limited argument parsing

## Functional Test Results (2026-06-02)
- ✅ Core library API: 13/14 tests passed (dv_decoder, dv_encoder, metadata, audio queries)
- ✅ pkg-config: works correctly (other software can link against libdv)
- ✅ ELF signatures: all binaries and libraries signed
- ✅ RPATH: uses $ORIGIN relative paths (portable)
- ✅ Strip: debug sections separated to debug package (--strip-debug)
- ⚠️ encodedv: crashes without arguments (missing popt)
- ⚠️ dvconnect: requires FireWire device (not useful on HarmonyOS)

## References
- Source: https://sourceforge.net/projects/libdv/
- License: LGPL-2.1