# SPIRV-Headers vulkan-sdk-1.3.290.0

Conan package for the Khronos SPIR-V headers and machine-readable grammar files.

## Build

```bash
conan create . -pr ohos-native
```

The package is header-only. The source archive is downloaded from the official
KhronosGroup repository and verified with the SHA-256 value in `conandata.yml`.

## Validation

`test_package` compiles C and C++ consumers against the public headers. The
tests check the SPIR-V magic number, version, `SpvOpNop`, and matching C/C++
opcode values.
