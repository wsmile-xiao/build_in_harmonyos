# critnib 1.1 notes

## Upstream census (R51)

- Source: https://github.com/kilobyte/critnib tag v1.1 (15210 bytes,
  sha256 1e5b65f815b0c23f74ce70cfcc2d8c9570cebc17a70e2a2e6e894c1b68297354)
- Build system: CMake (CMakeLists.txt + tests/CMakeLists.txt)
- Upstream tests: 4 ctest cases — 1corr, inequal, th, iter
  (tests/1corr.c, tests/inequal.c, tests/th.c, tests/iter + iter-cli.c;
  helpers hmload.c/rand.c). Registered via add_test() in tests/CMakeLists.txt.
- test_package: test_critnib.c, 6 assertions
  (new/insert/get/find_le+find_ge/remove/iter).

## Build

- Direct compiler invocation, no CMake configure step. Two CMake routes
  both fail compiler-ID on device with /data/service/hnp/bin/clang
  ("The C compiler identification is unknown"): conan CMakeToolchain
  default (no HarmonyOS platform module in stock CMake) and bare NDK
  ohos.toolchain.cmake (file not discoverable under the assumed SDK glob;
  profile sets no user_toolchain). The Linux-override CMake variant was
  tried next and still hit the same ID failure with writable TMPDIR
  already applied, so this round drops CMake try_compile probes entirely:
  the library is a single TU, compiled straight with the validated profile
  compiler and archived; the 4 upstream harnesses are compiled the same way
  (name.c+hmload.c+rand.c with -fcommon, iter-cli) and run for real — same
  sources/cases as ctest, without the broken probe. A cc smoke test runs
  first so a genuinely broken toolchain shows real stderr.
- Compiler validation (naga precedent, adapted): conf absolute c-compiler
  path stays preferred; PATH fallback only when missing/non-executable.
  Main recipe and test_package use the same rule.
- Writable TMPDIR guard kept (HMBS readonly_tmp: device /tmp is read-only).

## Patches

- patches/0001-cmake-ohos-compat.patch:
  - cmake_minimum 2.8.12 -> 3.16 (old minimum rejected by modern CMake)
  - SHARED-only -> BUILD_SHARED_LIBS aware (repo static-by-default)
  - `-latomic` -> find_library conditional (aarch64 inline atomics)
  - pod2man man page -> optional (missing perl on device/CI)
  - install() gains ARCHIVE destination for static .a
  - (Kept for CI/source consistency; direct-cc build links without
    -latomic first and retries with it only on __atomic link errors.)

## HMBS evidence

- build() compiles and runs 1corr/inequal/th + sh iter for real and emits
  HMBS_UPSTREAM_TEST_RESULT (framework direct-cc) with real counts
  (discovered/executed/passed/failed/skipped).
- test_package runs ./test_critnib and emits
  HMBS_TEST_PACKAGE_RESULT with discovered=6/passedCount=6.
- No tests skipped; no stubs; numbers come from framework output.
