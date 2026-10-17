# googletest 1.18.0

## Adaptation

- Uses the official `v1.18.0` release archive and commit.
- Builds GoogleTest and GoogleMock with CMake and C++17, including both
  upstream CTest suites.
- Keeps the package static by default and exports the four upstream CMake
  components through Conan.
- Treats HarmonyOS as Linux for the upstream help-output test because the
  target's `uname` value is `HarmonyOS` while its POSIX behavior is Linux-like.
- Makes `CapturedStream` honor `TMPDIR` when the OHOS sandbox does not permit
  writes to `/tmp`, while preserving the upstream `/tmp/` fallback.

## Validation boundary

The fresh Windows host build completed its platform-specific CTest inventory at
62/62 and the consumer at 3/3. MinGW intentionally excludes
`gmock_stress_test` because upstream does not support pthreads on that host;
forcing `GTEST_HAS_PTHREAD` is invalid because `Threads::Threads` is not
created. The OHOS W3 inventory contains that target and completed 63/63 plus
the Conan consumer at 1/1 after native self-signing of 68/68 target artifacts.

Platform AI Review for PR #8439 reported no code issue on the original recipe
HEAD. CI #40561 failed before source extraction because that worker had neither
`curl` nor Python SSL support; it is infrastructure evidence, not a package
test result. A current complete-head platform CI PASS is still required before
submission.
