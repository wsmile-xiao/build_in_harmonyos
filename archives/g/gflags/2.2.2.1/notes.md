# gflags 2.2.2 HarmonyOS PC adaptation

## Dependency boundary

gflags requires only the platform C++ runtime and pthreads. Upstream CMake
detects pthread through `find_package(Threads)`; there are no third-party Conan
requirements. The package builds the threaded shared library and disables the
optional no-threads variant.

## Build

The recipe uses Conan's `CMakeToolchain` with `OHOS_ARCH=arm64-v8a`. It enables
all upstream tests and runs CTest during a native HarmonyOS Conan build. The
shell-completion helper is excluded from the library package, so
`commands.json` is not required.

The OHOS build creates both shared and static gflags targets. Patch 0001 makes
the upstream test executables use the static target when CMake reports either
`OHOS` or `HarmonyOS`; this avoids HarmonyOS musl's unreliable relative DSO
lookup during target tests. `INSTALL_STATIC_LIBS=OFF` keeps the Conan shared
package unchanged: only `libgflags.so` is installed.

On case-insensitive Windows filesystems, the upstream Bazel file `BUILD`
collides with Conan's default `cmake_layout()` directory `build/`. The recipe
uses `conan-build/` for its local build and generator files to keep cross-build
verification reproducible.

## Verification

On 2026-07-18, community OHOS Conan 2.29.1 and DevEco OHOS Clang 15.0.4
completed `conan create`, cross-compiled `libgflags.so.2.2.2`, all five upstream
test executables, and the consumer test. CTest discovered 51 tests. The test
executables linked by patch 0001 do not need `libgflags.so`; the package still
contains only the shared library. The shared library is ELF64 AArch64, has
SONAME `libgflags.so.2.2`, and needs only `libc++_shared.so` and `libc.so`.

On 2026-07-24, the five upstream test executables, Conan consumer executable,
and `libgflags.so.2.2.2` were transferred to a HarmonyOS PC aarch64 device.
All ELF files were self-signed in their final HMDFS paths before execution. The
original 51-test CTest definition was relocated to the device without changing
test names or expectations. All 51 upstream tests passed, and the Conan
consumer test passed with `gflags answer=42`, for a total of 52/52 target tests.

The transferred test bundle SHA256 was
`27561809bf709a48c25aa67a6519fe24eb5c07eb7d1675d0984923fd8c2bb9da`.
After in-place signing, the consumer SHA256 was
`eb0b3951d31e8b6a71c25230a3f967efc6312d4273377756988d7cf09ab772f1`
and the shared library SHA256 was
`398423f21e30f2dbbc1a66f27ccd8aac08b3c8a6d36608e43ba651b93ec5307a`.

Local Conan verification used the CI-equivalent mirror fallback after the
official GitHub URL timed out; the source SHA256 remained enforced. The final
patch passed strict `git apply --check` against upstream 2.2.2 sources. CI
validation and publication remain separate remote gates.
