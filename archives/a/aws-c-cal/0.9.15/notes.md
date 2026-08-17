# aws-c-cal 0.9.15 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
source .build-context-aws-c-cal-0.9.15
cd $BUILD_SRC_DIR
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON \
  -DBUILD_TESTING=OFF -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_PREFIX_PATH="$AWS_COMMON;$AWS_LC"
cmake --build build -j$(nproc)
cmake --install build --prefix $TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure error: target "AWS::crypto" contains "Threads::Threads" but target not found | aws-c-cal CMakeLists.txt在else分支中调用find_package(crypto)前未先find_package(Threads)，而aws-lc的crypto-config.cmake依赖Threads::Threads | 在CMakeLists.txt中find_package(crypto)前添加find_package(Threads REQUIRED) |

## 源码修改

- **patches/0001-CMakeLists.txt.patch**: 在CMakeLists.txt的else分支中，find_package(crypto REQUIRED)前添加find_package(Threads REQUIRED)，并在PLATFORM_LIBS中添加Threads::Threads

## 依赖版本

- aws-c-common/0.14.3@ohpcd/stable (动态库 libaws-c-common.so)
- aws-lc/5.4.0@ohpcd/stable (静态库 libcrypto.a + libssl.a，OPENSSL_NO_ASM=ON)

## 验证结果

```bash
file $TEST_PREFIX/lib/libaws-c-cal.so
# ELF shared object, 64-bit LSB arm64

readelf -d $TEST_PREFIX/lib/libaws-c-cal.so | grep NEEDED
# NEEDED: libaws-c-common.so (from conan cache)
# NEEDED: libc.so
# libcrypto.a from aws-lc is statically linked (not shown as NEEDED)
```

## 注意事项

- aws-c-cal非系统同名库，默认动态链接(BUILD_SHARED_LIBS=ON)
- aws-lc作为静态库(libcrypto.a)，通过CMAKE_PREFIX_PATH被Findcrypto.cmake找到
- aws-c-cal链接aws-lc的静态libcrypto.a，依赖链通过conan管理
- CMake在HarmonyOS上会有"System is unknown"警告，不影响编译
---

**编译结束**: 2026-07-27 12:57
**最终状态**: built

## 最终状态

COMPLETED — aws-c-cal 0.9.15 适配完成，状态: built
