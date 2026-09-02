# munit

µnit is a small C unit-testing framework. This archive contains the Conan recipe for the official upstream `v0.2.0` tag on HarmonyOS PC.

- Upstream: https://github.com/nemequ/munit
- License: MIT
- Build system: upstream raw Makefile plus a Conan-owned library build
- Conan package: `munit/0.2.0`
- Dependencies: none
- Commands: none; this is a library package

The recipe packages `munit.h` and a static or shared `munit` library. The default is static, matching the upstream single-file implementation and avoiding an unnecessary runtime dependency for consumers. On OHOS, the test runner uses a recipe-owned writable `MUNIT_TMPDIR` because the device `/tmp` is not writable; the packaged library behavior is otherwise unchanged.
