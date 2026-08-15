# gd 2.3.3.2 OpenHarmony Adaptation Notes

## Scope

This recipe is a Path A adaptation of the core GD image library with CMake,
kept under the 2.3.3.2 package suffix because 2.3.3 is already published.
It does not claim a knowledge-base contribution, multi-library scope, a Path C
candidate, or complete OpenHarmony coverage of the GD feature matrix.

The default package deliberately disables PNG, JPEG, TIFF, WebP, AVIF, HEIF,
XPM, Freetype, Fontconfig, Raqm, the C++ API, documentation, and command-line
helpers. The retained surface is the in-memory C image API.

## Build Configuration

- Build system: CMake.
- Package modes: static by default, shared controlled by the Conan option.
- The default recipe disables the top-level `tests`, `examples`, and `docs`
  subdirectories before configuration. Set
  `-o gd/*:with_upstream_tests=True` on a runnable OpenHarmony PC to retain
  `tests` and `examples`, enable `BUILD_TEST`, and execute CTest after build.
- The official 2.3.3 release archive lists a nonexistent `tests/gdmatrix`
  directory and the missing `bug00320.c` / `bug00415.c` sources. Test mode
  comments out only those three stale list entries before CMake configuration;
  it does not alter the remaining upstream test sources.
- In static-only upstream-test mode, the release's `gdTest` helper links the
  unset shared target name `gd` even though CMake creates `gd_static`. The
  recipe redirects the test helper's variable to the existing `gd_static`
  target, preserving CMake's dependency graph instead of relying on a bare
  `-lgd` lookup or build ordering.
- The source transformation also empties `GD_PROGRAMS` and removes the
  `bdftogd` install command, so an initial library package does not claim
  unverified helper programs.
- On Windows static consumers, `BGDWIN32` and `NONDLL` remain scoped to the
  Windows package configuration; Linux and OHOS only add the system math
  library.

## Local Evidence

On 2026-08-01, a local Windows/MinGW preflight built and installed the core
static library. The installed `test_package/test_gd.c` consumer compiled and
ran with the Windows static-package definitions, passing 1/1 consumer program
and all 8 API checks.

The same preflight also completed Python syntax validation for the recipe and
test package (2/2) and checked the source-cropping transformation for repeated
application without further changes (1/1). These are local Windows results,
not OHOS results and not upstream-test results.

## Test Boundary

The upstream surface currently counted for this PR is 222 CMake test programs
plus 16 examples, or 238 entries. None has been executed for this recipe yet:
the factual upstream result is 0/238. On an accessible OpenHarmony PC, run
`conan create archives/g/gd/2.3.3.2 -pr:h=ci/conan/profiles/ohos-aarch64
-pr:b=ci/conan/profiles/ohos-aarch64 -o gd/*:with_upstream_tests=True
--build=missing --build=gd/*` and preserve the device CTest summary plus the
consumer CTest result. The actual device output, rather than this inventory,
is the only valid passed/total evidence.

With the default codec/font options still disabled, a host-side CMake
configuration probe registered 81 CTest entries after the release-list repair.
That is configuration evidence only, not an OpenHarmony result or a pass rate;
the device's CTest output determines the applicable passed/total count.

## Review Material

- PR: #3401.
- The remaining human template discussion stays open under the reviewer's
  control. Actual HarmonyOS PC upstream and consumer test results remain the
  required technical evidence for any later merge decision.
