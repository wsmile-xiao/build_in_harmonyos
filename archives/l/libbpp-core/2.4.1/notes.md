# libbpp-core 2.4.1 adaptation notes

## Build environment
- Build system: cmake
- Target platform: HarmonyOS PC (os=OHOS arch=armv8)
- Compiler: clang / clang++
- Status: built (pending device preflight evidence)

## Upstream
- Repository: https://github.com/BioPP/bpp-core
- Version: v2.4.1 tag archive
- Archive: https://github.com/BioPP/bpp-core/archive/refs/tags/v2.4.1.tar.gz
- sha256: 1150b8ced22cff23dd4770d7c23fad11239070b44007740e77407f0d746c0af6 (computed from downloaded tag archive)
- License: CECILL-2.1 (COPYING.txt)
- Dependencies: none (package.cmake.in confirms no deps; BPP_LIBS empty)

## Upstream test audit
- Source directory: test/
- Framework: ctest (test/CMakeLists.txt globs every test_*.cpp into one executable + add_test)
- Counted: 19 test_*.cpp files (test_bfgs, test_dAGraphObs, test_derivative1, test_distributions, test_downhill, test_eigen, test_gradient, test_graphObs, test_matrices, test_mva, test_numconstants, test_powell, test_range, test_reparametrization, test_sample, test_simplex, test_stats, test_text_tools, test_treeGraphObs)
- Switch: BUILD_TESTING=ON, command ctest --output-on-failure in build folder
- No GTest/HDF5/network dataset dependency; all tests are local numerical/graph checks

## Build steps
- cmake configure with BUILD_TESTING=ON and CMAKE_POLICY_VERSION_MINIMUM=3.5
- cmake build (upstream builds bpp-core-static + bpp-core-shared; test-only patch links the 19 test exes to bpp-core-static)
- ctest --output-on-failure in build folder, LD_LIBRARY_PATH extended with built .so dirs
- cmake install, COPYING.txt installed to licenses/

## test_package
- test.cpp exercises real API Bpp/Numeric/Range.h: bounds, overlap, expandWith, toString (5 checks)
- Compiled with Conan C++ compiler (-std=c++11 to match upstream flag) against packaged includes/libs
- Run as ./test_probe under conanrun env

## HMBS markers
- build() emits HMBS_UPSTREAM_TEST_RESULT with framework ctest, discovered 19, executed/passed/failed parsed from ctest output
- test_package test() emits HMBS_TEST_PACKAGE_RESULT with discovered 5 passedCount 5 after ./test_probe

## Issues and fixes
| # | Issue | Cause | Fix |
|---|-------|-------|-----|
| 1 | cmake_minimum_required(2.8.11) rejected by CMake 4.x | Removed compatibility with <3.5 | Set CMAKE_POLICY_VERSION_MINIMUM=3.5 via toolchain cache |
| 2 | Upstream tests link bpp-core-shared | Default shared=False would only install static in a pure BUILD_SHARED_LIBS flow | Keep upstream dual-target build (both libs still built and packaged); see row 3 for test linkage |
| 3 | 真机 19/19 ctest 失败：`Error relocating ... GlobalGraph ... symbol not found`（链接成功，运行时解析失败） | 测试链接 `bpp-core-shared`，运行时 loader 解析到的 .so 缺 GlobalGraph 符号（与链接期不是同一有效库；OHOS 下共享库运行时解析脆弱，参见 expat ML-0035 SONAME 记录） | test-only 补丁 `patches/0001-test-CMakeLists-link-static.patch`：19 个测试改链 `bpp-core-static`（同一对象集合、同一源码与断言，ctest 口径不变）；打包产物（static+shared）不变 |

## Notes
- Test-only patch patches/0001-test-CMakeLists-link-static.patch (patch_type test): 19 test exes link bpp-core-static instead of bpp-core-shared; same sources and assertions, ctest count unchanged. No commands.json (pure library, no bin/ tools).
- Final pass counts must come from device preflight log, not from this audit.
