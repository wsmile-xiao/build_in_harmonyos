# re2 2024-04-01 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-08
- 编译器: clang/clang++ 15.0.4
- 状态: published

## 编译步骤

re2 使用 CMake 构建系统，依赖 abseil-cpp。

```bash
# 1. conan install abseil-cpp 依赖
conan install . -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 -r=ohpcd --build=missing

# 2. CMake configure
cmake .. -DCMAKE_TOOLCHAIN_FILE=conan_toolchain.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DBUILD_SHARED_LIBS=OFF \
  -DRE2_BUILD_TESTING=OFF \
  -DCMAKE_PREFIX_PATH=<abseil-cpp package dir>

# 3. Build
make -j2

# 4. Install
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | find_package(absl) not found | abseil-cpp conan recipe uses cmake_file_name="abseil-cpp", not "absl" | Set absl_DIR to abseil-cpp package's lib/cmake/absl/ which has the original abslConfig.cmake with proper absl::* targets |
| 2 | Test package CMakeToolchain conflict | generators attribute + generate() method both create CMakeToolchain | Remove CMakeToolchain from generators, keep CMakeDeps only |
| 3 | RE2::Replace API mismatch | Replace takes std::string* not const char* | Fix test to pass &str instead of string literal |

## 源码修改

无补丁，re2 2024-04-01 在 OpenHarmony 平台上编译无需源码修改。

## 依赖版本

- abseil-cpp/20260107.1 (from ohpcd artifact repository)

## 验证结果

```bash
# conan-verify G2 (conan create) passed
# conan-verify G3 (system lib isolation) passed
# conan-verify G4 (product integrity) passed
# test_package: FullMatch, PartialMatch, Replace all passed
```

## 交付物

| 文件 | 说明 |
|------|------|
| conanfile.py | Conan recipe with abseil-cpp dependency |
| conandata.yml | Source URL + SHA256 |
| test_package/test.cpp | C++ smoke test using re2 API |
| test_package/conanfile.py | Test package with absl_DIR workaround |
| test_package/CMakeLists.txt | CMake config for test |
| test_package/MANIFEST.yml | Upstream test declaration |

## 注意事项

- abseil-cpp conan recipe 使用 cmake_file_name="abseil-cpp" 但 re2 的 CMakeLists.txt 调用 find_package(absl)，需要通过 absl_DIR 指向 abseil-cpp 二进制包的 lib/cmake/absl/ 目录（与 protobuf/33.6 相同的模式）
- re2 默认静态编译 (BUILD_SHARED_LIBS=OFF)
- 编译器警告：abseil-cpp 20260107.1 中 MutexLock/ReaderLock 等已标记为 deprecated，re2 2024-04-01 使用了这些 API，但不影响编译和功能
---

**编译结束**: 2026-08-08 04:02
**最终状态**: built
