# SPIRV-Cross 1.4.341.0

Conan package for the Khronos SPIRV-Cross libraries and command-line tool from
the `vulkan-sdk-1.4.341.0` release tag.

## Build

```bash
conan create . -pr ohos-aarch64
```

The package builds the static C/C++ backend libraries and the `spirv-cross`
executable. Upstream's optional external test dependencies are disabled.

## Validation

`test_package` parses an embedded SPIR-V compute module through the installed C
API, generates GLSL, writes the module to disk, and converts it again with the
installed CLI.
