# libjpeg-turbo 3.2.0.1 · HarmonyOS PC

## Existing recipe and this upgrade

The earlier 3.2.0 archive built and signed shared libraries, but set
`WITH_TOOLS=OFF` and `WITH_TESTS=OFF`. Upstream CMake explicitly disables the
regression suite when tools are off. Its Conan consumer only loaded
`libjpeg.so` and resolved one symbol. This upgrade enables and runs the full
suite and checks actual JPEG data flow through both public APIs.

The published `3.2.0` recipe is retained unchanged. The revised Conan package
uses version `3.2.0.1` because the registry cannot publish a different recipe
under an existing version (CI rule R37); the upstream source remains 3.2.0.

The recipe still discovers the OHOS SDK's `ohos.toolchain.cmake` and installs
to `lib/`. It keeps `WITH_SIMD=OFF`: earlier device work recorded an OHOS SIMD
link failure (E096), and this change does not claim to resolve it. The two
real `.so` files are re-signed after install so they can be loaded on the PC.
The package has no Conan or other third-party build dependency; CMake and the
OHOS Clang toolchain are already part of the target environment.

## Source and test inventory

- Official release: `https://github.com/libjpeg-turbo/libjpeg-turbo/releases/download/3.2.0/libjpeg-turbo-3.2.0.tar.gz`
- SHA-256: `6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e`
- Upstream `ctest -N` with `WITH_TESTS=ON`: 332 cases. Names comprise 52
  `tjunittest*` API cases and 280 other codec, command-line, image comparison,
  example, and BMP checks.
- No upstream test source was changed. Upstream Java/JNA tests were not
  registered because the optional JNA interface is disabled by default.

## HarmonyOS PC verification · 2026-10-10

Device: HarmonyOS PC AArch64, SDK 26.0.0.18, Conan 2.29.1, Clang 15.0.4,
CMake 4.1.2. The source tarball matched the SHA-256 above.

`conan create archives/l/libjpeg-turbo/3.2.0` using the repository's
`ci/conan/profiles/ohos-aarch64` as both host and build profile completed.
Its build ran all 332 upstream CTest cases: **332 passed, 0 failed, 0 skipped**
(110.88 seconds). The generic TurboJPEG RGB memory encode/decode case passed
(637-byte JPEG, decoded pixels within tolerance). The independent HarmonyOS
case wrote a JPEG to a UTF-8 path with spaces under `/storage/Users/currentUser`,
read it back via the libjpeg API, checked dimensions and pixels, and passed.
New tests: **2 passed, 0 failed**, including **1 HarmonyOS-specific end-to-end
case**. Both cases link to the packaged, signed shared libraries.

Evidence: `/storage/Users/currentUser/libjpeg-turbo-320-b-src/conan-create.log`
and `ctest-baseline.log` in this task's separate device work area.
That run exercised the revised recipe before its package version was incremented;
the `3.2.0.1` reference awaits CI validation.
