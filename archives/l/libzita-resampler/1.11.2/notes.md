# libzita-resampler 1.11.2

The upstream release uses a hand-written Makefile and has no automated test target.
The recipe overrides its native `-march` default for portable OHOS armv8 builds and
installs the shared library, headers, and a pkg-config module consumed by audiowmark.

## HarmonyOS validation

`conan create` completed with `EXIT=0` on OHOS armv8. The consumer test passed 1/1,
including setup, resampling from 48 kHz to 44.1 kHz, and a non-zero output assertion
(60,146 samples produced). The test package uses Ninja and signs the executable on
HMDFS before execution when `binary-sign-tool` is available.
