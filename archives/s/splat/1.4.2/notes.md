# splat 1.4.2 adaptation notes

## Build environment

- Target: OHOS 6.0, aarch64
- Compiler: clang/clang++ 15
- Build system: upstream custom shell scripts, reproduced directly in Conan
- Status: built

## Build approach

The upstream interactive `configure` script only chooses memory limits and then calls hard-coded `g++`/`cc` commands. The Conan recipe writes the conservative upstream-equivalent `MAXPAGES=4` configuration and compiles the same C/C++ sources with compilers from `tools.build:compiler_executables`. It compiles `splat.cpp`/`itwom3.0.cpp` twice to reproduce upstream's `splat` (`HD_MODE 0`) and `splat-hd` (`HD_MODE 1`) binaries.

Dependencies are declared as `bzip2/1.0.8` and `zlib/1.3.1`; include and library paths come only from Conan package metadata. No source patch is required.

## Upstream test inventory

The 38-file upstream release has no `test/` or `tests/` directory, no `make check`/`make test`/CTest registration, and no standalone self-test. Therefore the official upstream test count is 0, not skipped.

## Added tests

1. `test_splat.sh`: installed-package integration test covering all eight commands, real `bearing` computation from two QTH files, and SPLAT!/SPLAT! HD version output.
2. `test_ohos.sh`: OHOS-specific test that uses writable `TMPDIR`, executes packaged `usgs2sdf` by absolute path, and validates its public usage output (ref: E002).

Both tests passed through `conan create` with the repository OHOS aarch64 profile.

## Verification

```text
conan create archives/s/splat/1.4.2 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
Result: PASS
Upstream tests: 0/0 (upstream provides none)
Added tests: 2/2 PASS
```
---

**编译结束**: 2026-10-07 18:35
**最终状态**: built
