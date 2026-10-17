# JsonCpp for OpenHarmony PC

JsonCpp is a C++ library for parsing, generating, and manipulating JSON.
The `1.9.8` archive is the dependency package required by Redex.

## Adaptation

- Upstream version: 1.9.8
- Build system: CMake
- External dependencies: none
- Conan package modes: one shared library or one static library
- Disabled upstream artifact: object library
- Upstream logical tests: 223
- Consumer test flows: 3

HarmonyOS CMake does not provide the complete shared-library linker contract
in the validated environment. The recipe supplies the missing SONAME and
build-RPATH flags. A HarmonyOS-only source patch also suppresses upstream
`VERSION`/`SOVERSION` symlink generation, producing one real
`libjsoncpp.so` whose SONAME is its basename.

## Issue

- Dependency issue: https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos/issues/1268
