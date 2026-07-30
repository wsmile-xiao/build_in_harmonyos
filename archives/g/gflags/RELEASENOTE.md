# gflags HarmonyOS PC release note

## 2.2.2

- Migrated the legacy partial archive to a Conan 2 CMake recipe.
- Builds the threaded shared library for OHOS AArch64; an OHOS/HarmonyOS-only
  CMake patch links upstream tests to a non-installed static test target.
- Compiles all five upstream test executables; CTest discovers 51 tests.
- Adds a consumer test that calls `SetCommandLineOption` and verifies the flag
  value through the packaged API.
- Publication remains pending until the dependency PR is reviewed, merged and
  the release pipeline uploads `gflags/2.2.2`.
