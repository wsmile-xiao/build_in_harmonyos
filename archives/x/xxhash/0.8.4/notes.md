# xxHash 0.8.4 — HarmonyOS PC build notes

## Source and build

- Upstream release tag: `v0.8.4` from `Cyan4973/xxHash`.
- Source archive: official GitHub codeload endpoint; SHA-256 is recorded in `conandata.yml`.
- The 0.8.4 release moved its CMake project from `cmake_unofficial` to `build/cmake`; the recipe uses the new location.
- The package builds the shared `libxxhash` library and public headers. It has no Conan dependencies and applies no source patches.
- The recipe discovers the OHOS toolchain from the profile, `OHOS_NDK_HOME`, the CI SDK layout, or the Harmonybrew SDK Cellar. It also finds the SDK `llvm-objcopy` and `binary-sign-tool` when packaging the signed shared library.

## Validation

- Device: HarmonyOS PC, aarch64, Clang 15.0.4, Conan 2.29.1.
- `conan create archives/x/xxhash/0.8.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing`: exit 0.
- Upstream `make check`: passed. `tests/sanity_test.c` reported `OK. (passes 49948 tests)`; all 10 `xxhsum` CLI workflows in the `Makefile` check target completed successfully.
- Conan consumer test: 13/13 checks passed, covering package version, XXH32/XXH64/XXH3 reference vectors, input sensitivity, and XXH64/XXH3 streaming.
- Upstream tests and sources were not modified.
