# nghttp3 1.15.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-07
- 编译器: clang/clang++ (15.0.4)
- 状态: published

## 编译步骤

```bash
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON
make -j2
make install DESTDIR=$TEST_PREFIX  # staging
ctest --output-on-failure  # tests
make install  # actual install
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake warnings "System is unknown to cmake" | HarmonyOS not recognized by CMake platform detection | Non-fatal warning, CMake still configures correctly using clang compiler |
| 2 | Test target `main` not built by default | Tests use `EXCLUDE_FROM_ALL` in CMakeLists.txt | Explicitly build test target: `make main` then run `ctest` |

## 源码修改

- patches/0001-config.guess.patch: Add HarmonyOS/OpenHarmony platform detection to config.guess (for autotools compatibility; CMake build doesn't use config.guess)

## 依赖版本

无依赖

## 验证结果

```bash
ctest --output-on-failure
# 100% tests passed, 0 tests failed out of 1
# Test #1: main .............................   Passed    0.18 sec
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libnghttp3.so | Shared library |
| lib/libnghttp3.a | Static library |
| include/nghttp3/nghttp3.h | Public header |
| include/nghttp3/version.h | Version header |
```
---

**编译结束**: 2026-08-07 04:59
**最终状态**: published
