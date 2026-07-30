# mt32emu

mt32emu is the Munt C/C++ library for emulating Roland MT-32, CM-32L,
and LAPC-I synthesizer modules.

## Features

- C and C++ consumer APIs
- Built-in sample-rate conversion
- Shared and static library builds
- CMake package target `MT32Emu::mt32emu`
- pkg-config module `mt32emu`

## OHOS adaptation

- Configures only the standalone `mt32emu/` library subdirectory.
- Keeps the upstream built-in resampler enabled, so no external resampler
  package is required.
- Excludes the Qt UI, SMF-to-WAV tool, and platform drivers from the build.
- Supports shared and static Conan package IDs.
- Avoids versioned shared-library symlink chains on OHOS/HMDFS.
- Sets `CMAKE_POLICY_VERSION_MINIMUM=3.5` for CMake 4.x compatibility with
  the upstream 2.8.12 declaration (project knowledge E187).
- Tests the installed C ABI through version and inventory queries, context
  lifecycle, renderer selection, and the expected missing-ROM boundary.
- Uses Path A+B: the software and paired `E252-draft-MT32` knowledge draft are
  submitted together without changing the formal knowledge index.

## Dependencies

- Build dependencies: CMake and a C++ compiler
- Third-party library dependencies with the default configuration: none
- Runtime assets for full synthesis: user-supplied compatible control and PCM
  ROM images

## References

- Upstream repository: https://github.com/munt/munt
- Upstream tag: `libmt32emu_2_7_1`
- License: LGPL-2.1-or-later
