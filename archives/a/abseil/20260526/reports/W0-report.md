# abseil 20260526 W0 dependency report

Date: 2026-08-12

## Result

Production dependency preflight: **pass**.

| Dependency | Kind | Publication check | Decision |
|------------|------|-------------------|----------|
| Threads | system | Not a Conan package | Required; provided by the OHOS toolchain as `libpthread` |
| `gtest/1.17.0` | test-only | Recipe and OHOS armv8 binary published on `ohpcd` | Declare with `test_requires`; never expose it to package consumers |

Abseil has no production third-party Conan dependencies, so no dependency is
mixed into issue 2073. GoogleTest was adapted and published separately before
this PR enabled the upstream suite.

## Evidence

- Upstream top-level CMake calls `find_package(Threads REQUIRED)`.
- GoogleTest setup is guarded by `BUILD_TESTING AND ABSL_BUILD_TESTING`.
- The source inventory contains 241 `absl_cc_test()` declarations and 247
  referenced test source files.
- Isolated shadow CI resolved `gtest/1.17.0` under `Test requirements`, not
  `Requirements`.
- The OHOS binary resolved from `ohpcd` with package ID
  `21b17f8b2bc0e9511e276e3d57a23893067cefe5` and package revision
  `489a70cbb1156b4d5594f8ce638b9630`.
- The package's production dependency graph remains one Abseil node plus the
  platform Threads library.

## Profile

- OS: HarmonyOS/OHOS 6.0, armv8.
- Compiler: clang 15, libc++, C++17, Release.
- Conan: 2.29.1.
- Package: static, position independent.

No additional dependency library or dependency PR is blocked.
