# SPIRV-Tools 1.4.321.0-r1 adaptation notes

## Scope

- Package: spirv-tools/1.4.321.0-r1
- Upstream tag: vulkan-sdk-1.4.321.0
- Issue: #805

## Adaptation

- Added a Conan CMake recipe for SPIRV-Tools.
- Downloads matching SPIRV-Headers and places them under `external/spirv-headers` before configuration.
- Supports static and shared library builds through the Conan `shared` option.
- Skips executables and upstream tests to keep the CI build focused on reusable dependency artifacts.
- Maps OHOS CMake system name to Linux for SPIRV-Tools platform checks.

## Tests

- Added a `test_package` that checks public headers and the selected static or shared libraries.
- The test compiles and links a C++ program against the selected `SPIRV-Tools` library artifact.
- When the target is runnable, the program assembles SPIR-V text to binary and validates the result through the SPIRV-Tools C API.

## Local Validation

- `python -m py_compile` was run for recipe/test files.
- `git diff --check` passed.
- Full OHOS `conan create` requires the remote CI environment.
