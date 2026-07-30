# SPIRV-Headers vulkan-sdk-1.3.290.0 adaptation notes

## Source

- Upstream tag: `vulkan-sdk-1.3.290.0`
- Upstream commit: `2acb319af38d43be3ea76bfabf3998e5281d8d12`
- Archive SHA256:
  `1b9ff8a33e07814671dee61fe246c67ccbcfc9be6581f229e251784499700e24`
- Source patches: none

## Package

SPIRV-Headers is a header-only package. The recipe installs the complete
`include/spirv` tree, upstream CMake package metadata, pkg-config metadata,
and the upstream license. The generated pkg-config include path is rewritten
to remain relocatable inside the Conan package.

## Upstream Tests

The tagged source contains three compile-based integration scenarios:

1. `tests/example.cpp` through the in-tree CMake target;
2. `tests/find_package/CMakeLists.txt` against the staged CMake package;
3. `tests/pkg_config/CMakeLists.txt` against the staged pkg-config file.

The recipe executes all three scenarios without modifying upstream tests.
The `find_package` scenario still declares CMake 3.0, so the recipe sets
`CMAKE_POLICY_VERSION_MINIMUM=3.5` when configuring that unchanged test with
the newer CMake used by competition CI.

## Consumer Test

The Conan `test_package` compiles through
`SPIRV-Headers::SPIRV-Headers`. On runnable platforms it validates four
public constants: the SPIR-V magic number, version, C opcode, and matching
C++ opcode.

## Validation Status

Native Linux validation passed on 2026-07-26 with Conan 2.29.1, CMake 3.25.1,
GCC 12.2.0, and pkg-config 1.8.1:

```bash
conan create . -pr:h=default -pr:b=default --build=missing
```

- Upstream integration scenarios: 3/3 passed.
- Conan consumer assertions: 4/4 passed.
- OHOS AArch64: not run locally; official competition CI is pending and
  remains the final platform acceptance signal.
