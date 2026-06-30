# libcue

libcue is a C library for parsing CUE sheet files. CUE sheets describe the layout of tracks on a CD, including track numbers, titles, and timing information.

## Available Versions

| Version | Status | Date | Functional Test |
|---------|--------|------|----------------|
| 2.3.0 | published | 2026-06-01 | ✅ 11/11 PASS |

## Description

libcue provides functions to parse CUE sheet files and extract disc, track, and index information. It uses flex and bison for parsing the CUE format.

## Build Notes

- Build system: CMake
- Requires: bison, flex
- Produces: static library (libcue.a), pkg-config file, header file
- Patch: `0001-CMakeLists.txt.patch` — cmake_minimum_required VERSION 2.8→3.5 (CMake 4.x兼容)

## HarmonyOS Platform Verification

### Quality Gates
| Gate | Result |
|------|--------|
| G1 Binary Integrity | ✅ PASS |
| G2 Functional | ✅ PASS |
| G3 Portability | ✅ PASS |
| G4 Archive Integrity | ✅ PASS |

### Functional Test Summary
- cue_parse_string / cue_parse_file: ✅ 正常解析
- Track extraction (filename, start, ISRC, INDEX): ✅ 正确
- REM / CDTEXT parsing: ✅ 正确
- Error tolerance (empty input): ✅ 不崩溃
- pkg-config: ✅ version/libs/cflags正确

### Known Warnings (non-blocking)
- CMake: "System is unknown to cmake, create: Platform/HarmonyOS"
- CMake: CMP0145 policy warning (Dart module deprecated)
- bison parser: stderr "syntax error" messages (不影响功能)