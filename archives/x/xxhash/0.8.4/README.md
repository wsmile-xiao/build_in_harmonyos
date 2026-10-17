# xxHash 0.8.4 for HarmonyOS PC

This Conan recipe packages the xxHash C library for `os=OHOS, arch=armv8`. It builds the shared library with the upstream CMake project in `build/cmake`; the `xxhsum` executable is not included in the package.

## Source

- Upstream: https://github.com/Cyan4973/xxHash
- Release tag: `v0.8.4`
- Source archive: `https://codeload.github.com/Cyan4973/xxHash/tar.gz/refs/tags/v0.8.4`
- SHA-256: `5738270935e7c3d38a79b3adf7c9692566ce7895a25f67de43ad52ab504acd32`

## Build and validation

There are no external dependencies or HarmonyOS-specific source patches. The recipe installs `libxxhash` and its public headers, then runs the upstream `make check` suite with the compiler selected by the OHOS CMake toolchain. `test_package` links a separate consumer against the Conan package and checks known vectors and streaming APIs.

## Conan consumer

```bash
conan install --requires=xxhash/0.8.4 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

The package exposes the `xxhash` library and `xxhash::xxhash` CMake target through Conan generators.
