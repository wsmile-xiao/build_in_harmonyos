# libjpeg-turbo 3.2.0.1 test report · HarmonyOS PC

Date: 2026-10-10 (Asia/Shanghai)

## Environment and source

- HarmonyOS PC AArch64; OHOS SDK 26.0.0.18; Clang 15.0.4; CMake 4.1.2;
  OHOS-enabled Conan 2.29.1.
- Official 3.2.0 tarball SHA-256:
  `6f30092cef9fb839779646608f4ee14ae3cbac989c47fa05e841b0841f09878e`.
- No third-party Conan package is required.

## Upstream tests

Configured with `WITH_TOOLS=ON`, `WITH_TESTS=ON`, `WITH_SIMD=OFF`,
`ENABLE_SHARED=ON`, and `ENABLE_STATIC=OFF` using the OHOS SDK CMake toolchain.
`ctest -N` registered 332 cases: 52 `tjunittest*` API cases and 280 other
upstream command-line, codec, image comparison, example, and BMP cases.

The recipe's `build()` executed:

```sh
ctest --test-dir build-ohos --parallel 4 --output-on-failure
```

Result: **332/332 passed, 0 failed, 0 skipped**; 110.88 seconds in the full
Conan build. Upstream test files were not changed. Optional Java/JNA tests
were not registered because the JNA interface is disabled by default.

## New consumer tests

| Case | Public API and behavior | Result |
| --- | --- | --- |
| `test.c` | TurboJPEG RGB buffer compression and decompression; verifies nonempty JPEG and every decoded component | Passed (1/1) |
| `test_ohos.c` | HarmonyOS AArch64 libjpeg encoding to a JPEG file in user storage with Chinese characters and spaces in the path, followed by file read, decode, dimension and pixel checks | Passed (1/1) |

New tests: **2/2 passed**, including **1/1 HarmonyOS-specific end-to-end
test**. The two executables linked against the packaged shared libraries after
the recipe signed them. No test was reclassified from the upstream suite.

## Reproduction

From the repository root on the device:

```sh
conan create archives/l/libjpeg-turbo/3.2.0.1 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

The independent device log is
`/storage/Users/currentUser/libjpeg-turbo-320-b-src/conan-create.log`.
It records the revised recipe tested under package reference `3.2.0` before
the registry collision required version `3.2.0.1`. Build and test logic is
unchanged; the new package reference has not yet been retested on the device.
