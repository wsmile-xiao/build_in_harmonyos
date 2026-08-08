# aces_container 1.0.2 adaptation notes

## Source

- Upstream: https://github.com/aces-aswf/aces_container
- Selected version: v1.0.2
- Source archive: https://github.com/aces-aswf/aces_container/archive/refs/tags/v1.0.2.tar.gz
- SHA-256: cbbba395d2425251263e4ae05c4829319a3e399a0aee70df2eb9efb6a8afdbae

## Build

- Build system: CMake
- Conan dependencies: none
- Default package build: static library, position-independent code enabled
- Patch: raise the CMake minimum version to 3.5, fix Clang C++17 narrowing diagnostics in two scanline headers, and repair installed CMake/pkg-config metadata.

## Tests

- Upstream tests: 0/0. The upstream release has no `enable_testing`, `add_test`, or tests directory.
- Added tests: 1/1. The Conan `test_package` builds a C++ consumer, writes a 1x1 ACES file, and checks return codes, output size, and magic bytes.

## OpenHarmony PC notes

- No OHOS-specific conditional macro is added to source or patches.
- The recipe uses the standard Conan CMake toolchain and does not require third-party packages.
---

**编译结束**: 2026-08-06 22:30
**最终状态**: built
