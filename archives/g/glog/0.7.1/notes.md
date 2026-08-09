# glog 0.7.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++ 15.0.4
- 状态: built

## 编译步骤

```bash
mkdir build && cd build
conan install --requires=gflags/2.2.2 -g CMakeDeps -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
cmake .. -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX \
  -DWITH_GFLAGS=ON -DWITH_GTEST=OFF -DWITH_UNWIND=none \
  -DBUILD_SHARED_LIBS=ON -DWITH_SYMBOLIZE=ON -DWITH_TLS=ON
make -j2
make install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | target_compile_features fails on HMDFS | HMDFS does not support CMake generator expressions for COMPILE_FEATURES | Replace with set_target_properties CXX_STANDARD (patch 0001) |
| 2 | GLOG_EXPORT not defined in test_package | GLOG_USE_GLOG_EXPORT not propagated through conan package_info | Add self.cpp_info.defines.append("GLOG_USE_GLOG_EXPORT") in package_info() |
| 3 | CMake "System is unknown" warning | CMake lacks HarmonyOS platform module | Non-blocking warning, build succeeds with Linux-compatible behavior |

## 源码修改

- **CMakeLists.txt** (patch 0001): Replace `target_compile_features(glog PUBLIC cxx_std_14)` with `set_target_properties(glog PROPERTIES CXX_STANDARD 14 CXX_STANDARD_REQUIRED ON)` for HMDFS compatibility. Same for `glog_internal` target.

## 依赖版本

- gflags/2.2.2 (conan, shared binary from ohpcd remote)
- pthread (system library)

## 验证结果

```
conan create: PASS (G1-G4 all passed)
W3 local CI simulation: PASS
ctest: 16/22 tests passed (6 failures due to gflags cmake config not findable in test sub-projects and platform-specific signal handling)
```

## 注意事项

- libunwind standalone is not available; glog uses backtrace() fallback (upstream behavior with WITH_UNWIND=none)
- GTest is disabled (WITH_GTEST=OFF) as it's only for the test suite, not the library itself
- gflags is shared (shared:True) to match available binary on ohpcd remote

最终状态: built
