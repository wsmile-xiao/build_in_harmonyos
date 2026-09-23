# cxxopts 3.2.0 adaptation notes

## Build environment

- Platform: OpenHarmony PC aarch64
- Compiler: clang/clang++ 15.0.4
- CMake: 4.1.2
- Conan: 2.29.1
- Build system: CMake
- Package type: header-only
- Status: built

## W0/W0b and source

- W0: preflight_check.sh cxxopts/3.2.0 passed; the recipe has no Conan dependencies.
- W0b: no same-version archive or notes existed. Existing cxxopts 3.3.1 was read and its CMake/header-only approach was used as a reference.
- Upstream tag: v3.2.0, commit 3bf268481da8208d171d8908e6491459de3651d7.
- Source URL: https://github.com/jarro2783/cxxopts/archive/refs/tags/v3.2.0.tar.gz
- Source SHA256: 9f43fa972532e5df6c5fd5ad0f5bac606cdec541ccaf1732463d8070bbb7f03b.

## Build and test commands

    cmake -S . -B build -DCMAKE_POLICY_VERSION_MINIMUM=3.5
      -DCXXOPTS_BUILD_TESTS=ON -DCXXOPTS_BUILD_EXAMPLES=OFF
      -DCMAKE_BUILD_TYPE=Release
      -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++
      -DCMAKE_CXX_FLAGS=-std=c++14
    cmake --build build -j1
    ctest --test-dir build --output-on-failure

The patched upstream suite completed with configure=0, build=0, test=0:
- Catch2 source inventory: 35 TEST_CASE declarations; 34 ran and passed.
- The std::optional TEST_CASE is guarded by CXXOPTS_HAS_OPTIONAL; it was not registered under the upstream C++11 test configuration, so 1 case was skipped with a documented condition.
- The skip is caused by compile-time registration: CXXOPTS_HAS_OPTIONAL is false under the upstream C++11 test configuration; the source case remains present and no test was deleted.
- Two CMake integration tests ran and passed.
- link_test compiled successfully but is not registered with CTest and is not counted as a test case.
- Consumer test_package builds and runs cxxopts::Options::parse with 3 behavior assertions.

## Upstream test issue and patch

The original upstream test suite built options_test and link_test, but both nested CMake integration tests failed on CMake 4.1.2 because their child projects declare cmake_minimum_required(VERSION 3.1). The first real error was:
Compatibility with CMake < 3.5 has been removed from CMake.

Patch 0001-test-CMakeLists.txt.patch passes -DCMAKE_POLICY_VERSION_MINIMUM=3.5 to both ctest --build-and-test child invocations. With the patch, all three registered CTest tests passed. No test was deleted or weakened.

## Adaptation

- No library source API changes were needed.
- conanfile.py uses package_type=header-library, installs the upstream header and CMake package config, and runs the upstream CTest suite in build().
- test_package is a real C++ consumer test that links the CMake target and executes the parser API.
- Existing knowledge E187 covers the CMake 4.x policy failure; this task is Path A, with no new cross-repository Path B knowledge.

### 对话 #1

- 2026-09-04: W0 and W0b passed; the upstream v3.2.0 tag and SHA256 were verified.
- 2026-09-04: The original nested CMake integration tests failed on CMake 4.1.2 because child projects requested compatibility below 3.5. The minimal patch passes CMAKE_POLICY_VERSION_MINIMUM=3.5 to both child builds.
- 2026-09-04: Conan create, the complete patched upstream CTest suite, the real consumer test_package, and W3 local CI passed. The test report records 37 static upstream cases, 36 executed, 36 passed, 0 failed, and 1 documented skip.
---

**编译结束**: 2026-09-05 15:09
**最终状态**: built
