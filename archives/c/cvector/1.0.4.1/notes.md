# cvector 1.0.4.1 HarmonyOS PC adaptation

## Upstream

- Repository: https://github.com/yayahjb/cvector
- Tag: `CVector-1.0.4.1`
- License: LGPL-2.1-only (`lgpl.txt`)
- Language: ANSI C (C89, `-ansi -pedantic` in upstream Makefile)
- Third-party dependencies: none
- Source tarball: https://codeload.github.com/yayahjb/cvector/tar.gz/refs/tags/CVector-1.0.4.1
- SHA256: `91ac076ed4b0ebb6053b2ce4d339a4f9712a760b76250fef1330c32a1b49fb10`

## Build system choice

Upstream ships two build systems:

- `Makefile` (libtool-based: `libtool --mode=compile/link/install`). Requires
  libtool, which is unavailable on HarmonyOS, and hardcodes
  `CVECTOR_PREFIX=/usr/local` install paths. Rejected.
- `CMakeLists.txt` (builds `CV_static`, `CV_shared`, `CVectorBasicTest`,
  registers 2 CTest cases, `cmake --install` support). Portable. Chosen.

Recipe uses `CMakeToolchain` + `cmake_layout`; no toolchain hacks, no
`__OHOS__` macros, no source patches except the minimal CMake
compatibility fix below.

## Patches

- `patches/0001-cmake-min-version.patch` (portability):
  - `cmake_minimum_required (VERSION 2.8.7)` -> `cmake_minimum_required(VERSION 3.15)`
    (modern CMake rejects `< 3.5` compatibility).
  - `set_target_properties(CVectorBasicTest PROPERTIES LINK_LIBRARIES ...)`
    -> `target_link_libraries(CVectorBasicTest PRIVATE CV_static)`
    (deprecated property form replaced by the canonical command; no behavior change).
  - `CBF_DEBUG_MESSAGE("Created directory ...")`
    -> `message(STATUS "Created directory ...")`
    (CBF helper is never defined in the shipped tree; configure failed at
    `CV_REQUIRE_DIRECTORY` with `Unknown CMake command "CBF_DEBUG_MESSAGE"`;
    same diagnostic level, no behavior change).

## Packaging notes

- Upstream `install()` ships `libCVector.a`, `libCVector.so`, and the
  `CVectorBasicTest` binary, but installs no headers. Recipe copies
  `CVector.h` to `include/` manually.
- `CVectorBasicTest` is an upstream test program, not a shipped CLI tool,
  so `bin/` is removed in `package()` (R38: pure library, no `commands.json`).
- Static-only packaging (`*.so*` removed): keeps the package minimal and
  avoids the upstream empty-`SOVERSION` shared-library gate issue.
- `package_info()`: `libs = ["CVector"]`,
  `cmake_file_name = "cvector"`, `cmake_target_name = "cvector::cvector"`.

## Upstream tests

CMake registers 2 CTest cases (`enable_testing()` in `CMakeLists.txt`):

1. `CVectorBasicTest` — runs `bin/CVectorBasicTest CVectorBasicTest.lst`;
   exercises create/add (1M doubles)/array access/get/pointer/set/remove/clear
   and writes the full log to `CVectorBasicTest.lst`.
2. `cmp-CVectorBasicTest_orig.lst-CVectorBasicTest.lst` — `cmake -E compare_files`
   of the generated list against `CVectorBasicTest_orig.lst`.

Recipe runs the full suite in `build()` via `cmake.test()`
(`ctest --output-on-failure`); no upstream test source or expected
output is modified.

## Consumer test

`test_package/test_cvector.c` links `cvector::cvector` and covers the full
public API: create, add (growth), array read-back, get, pointer access,
`CVectorElementAt`, set, contiguous-storage check, remove/shift, clear,
reuse-after-clear, free/null. ~80 assertions in one consumer boundary.

## Validation

- `git rev-parse --verify HEAD` succeeds on branch `feat/cvector-1.0.4.1`.
- `ci/conan/profiles/ohos-aarch64` exists.
- Awaiting HMBS preflight (conan create + upstream ctest + test_package)
  before any commit/push.
