# Draft: Preserve upstream CTest without an external GTest bootstrap

> Status: DRAFT | Source: Highway 1.3.0, OpenHarmony PC PR #3398

## Problem

A CMake project can gate its upstream tests behind `BUILD_TESTING`, while the
default test mode downloads or links an external framework such as GoogleTest.
Turning tests off keeps a package buildable but removes the upstream suite;
vendoring the framework adds a second source-provenance and maintenance path.

## Reusable observation

Before choosing either fallback, inspect whether upstream already ships a
native test runner compatible with the build system's discovery contract.
Highway 1.3.0 exposes `HWY_TEST_STANDALONE`. With it enabled, its CMake files
skip the GoogleTest bootstrap and link dependency, but its `hwy_gtest.h`
runner still accepts `--gtest_list_tests` and `--gtest_filter`. CMake's
existing `gtest_discover_tests()` registration can therefore retain the
upstream CTest suite.

For Highway, an opt-in Conan test configuration is:

```text
BUILD_TESTING=ON
HWY_ENABLE_TESTS=ON
HWY_ENABLE_CONTRIB=ON
HWY_TEST_STANDALONE=ON
```

The production default remains test-free. The test option must run CTest only
when `can_run(self)` is true, and the final PR must record the exact native
device command and passed/total count separately from its consumer test.

## Evidence boundary

This is source-derived draft knowledge, not a statement that the current
Highway package has passed on HarmonyOS PC. Native execution remains required
before publishing any rate or resolving a test-evidence review discussion.

## Do Not

- Do not call `HWY_TEST_STANDALONE=ON` a test pass before CTest ran on the
  target.
- Do not silently set `BUILD_TESTING=OFF` when upstream provides a maintained
  framework-free runner that can preserve the suite.
- Do not report CI or host results as HarmonyOS PC evidence.
