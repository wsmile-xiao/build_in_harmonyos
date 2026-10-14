# libjpeg-turbo 3.2.0.1 on HarmonyOS PC

This Conan package provides the libjpeg and TurboJPEG shared libraries for
HarmonyOS AArch64. It has no third-party package requirements.

The recipe uses the installed OHOS CMake toolchain, builds the upstream command
line tools and regression targets, and runs all 332 registered CTest cases
before packaging. SIMD remains disabled because the existing HarmonyOS recipe
documents an unresolved SIMD link issue. Installed shared objects are signed
for HarmonyOS execution.

Run the full build and tests on a HarmonyOS PC with the repository profiles:

```sh
conan create archives/l/libjpeg-turbo/3.2.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

The Conan test package then runs two additional cases: TurboJPEG RGB
compression/decompression with pixel checks, and a HarmonyOS-specific libjpeg
file round trip under the user storage directory using a UTF-8 path with spaces.
The latter is compiled only for HarmonyOS AArch64.
