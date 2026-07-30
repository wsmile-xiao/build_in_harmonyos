# SPIRV-Headers vulkan-sdk-1.3.290.0

This Conan recipe packages the official Khronos SPIR-V headers and
machine-readable grammar files.

## Validation

The build executes all three upstream integration scenarios:

1. the in-tree CMake target from `tests/example.cpp`;
2. the installed CMake `find_package` consumer;
3. the installed pkg-config consumer.

The separate Conan `test_package` compiles against the packaged
`SPIRV-Headers::SPIRV-Headers` target and validates four public constants.

Native Linux validation passes all three upstream integration scenarios and
all four consumer assertions. OHOS AArch64 validation is delegated to the
official competition CI.
