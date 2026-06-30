# bcpp — C(++) Beautifier

## Description
bcpp is a C/C++ source code beautifier/indenter. It reformats C and C++ source code to a consistent style with configurable indentation, brace placement, and spacing.

## Versions

| Version | Status | Date |
|---------|--------|------|
| 20250914 | published | 2026-06-25 |

## Build Information (20250914)
- **Build System**: autotools
- **Platform**: aarch64-unknown-linux-ohos (HarmonyOS)
- **Compiler**: clang/clang++ 15.0.4
- **Dependencies**: None (standalone C++ program)

## Patches
1. `0001-config.guess.patch` — E007: HarmonyOS/__OHOS__ platform detection
2. `0002-config.sub.patch` — E007: ohos-linux triplet support
3. `0003-configure.patch` — E011: HMDFS umask 077→022 fix

## Source
- URL: https://invisible-mirror.net/archives/bcpp/bcpp-20250914.tgz
- Format: tar.gz
