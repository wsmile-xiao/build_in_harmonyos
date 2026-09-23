# mtoc

`mtoc` converts a Mach-O executable into a PE/COFF image suitable for EFI
firmware. It is distributed in Apple's open-source cctools release.

## Function Overview

- Converts 64-bit Mach-O preload images to PE32+.
- Emits EFI application, boot-service driver, or runtime-driver subsystems.
- Preserves the input architecture and executable section payload.

## Available Versions

| Version | Status | Build System | Notes |
| --- | --- | --- | --- |
| 1035.1.102 | built | CMake wrapper | OHOS aarch64 Conan build and 18-assertion device test verified |

## Package Contents

- `bin/mtoc`: Mach-O to PE/COFF converter
- `share/man/man1/mtoc.1`: command manual

## HarmonyOS Adaptation

Apple builds mtoc as part of the Darwin/Xcode cctools tree. The HarmonyOS
recipe adds a focused CMake wrapper and uses non-Darwin headers plus the
`libstuff` portability shim from the cctools-port project. Both inputs are
pinned by archive SHA256; the conversion implementation remains Apple
1035.1.102. ARM compatibility-directory aliases are materialized for
HarmonyOS filesystems, and a small portability patch makes the imported
`strings.h` fallback safe under repeated inclusion.

## Dependencies

The package has no external Conan build or runtime dependencies. It uses only
the C toolchain and the platform C library.

## References

- Apple cctools: <https://github.com/apple-oss-distributions/cctools>
- cctools-port: <https://github.com/tpoechtrager/cctools-port>
