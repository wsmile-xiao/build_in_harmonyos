# SPIRV-Headers vulkan-sdk-1.3.290.0 adaptation notes

## Result

- Target: OHOS 6.0, armv8, clang 15 profile
- Date: 2026-07-16
- Status: `built`
- Source changes: none

## Implementation

The package copies the complete upstream `include/` tree, including the C/C++
headers and JSON grammar files. The source archive is pinned to the official
Khronos release tag and SHA-256 checksum.

## Validation

`conan create` completed successfully. The C and C++ consumer tests compiled
against the public SPIR-V headers and validated seven API assertions, including
matching C/C++ opcode values. The package integrity gates found the installed
header tree and no unexpected binary or system-library collision.
