# ittapi 3.28.2

- Builds the static `ittnotify` and `jitprofiling` libraries.
- Enables the upstream C++ wrapper so its eight standalone upstream tests are
  compiled, packaged, and executed by `test_package`.
- Disables IPT, Fortran, and the reference collector to avoid optional platform
  dependencies that are not part of the base API.
- Local OHOS arm64 `conan create` completed successfully: both libraries, all
  eight upstream test executables (8/8), and the consumer compiled and linked
  as AArch64 artifacts. Runtime execution is deferred because no OHOS arm64
  HDC target is connected.
- Official OHOS test and CI results remain pending.
