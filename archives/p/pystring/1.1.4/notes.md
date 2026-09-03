# pystring 1.1.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: built

## 编译步骤

```bash
# Source build context
source .build-context-pystring-1.1.4

# Build with CMake (need CMAKE_POLICY_VERSION_MINIMUM for old cmake_minimum_required)
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_CXX_COMPILER=clang++ -DCMAKE_C_COMPILER=clang \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j1
make install

# Test
make -f Makefile test CXX=clang++ CXXFLAGS="-g -O2 -Wall"
ctest
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: Compatibility with CMake < 3.5 has been removed | pystring's CMakeLists.txt uses cmake_minimum_required(VERSION 3.2), incompatible with CMake 4.x | Add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | BadZipFile: File is not a zip file | conan get() can't auto-detect archive format from URL without .tar.gz extension | Add filename="pystring-1.1.4.tar.gz" to get() call |
| 3 | L5 SONAME warning: libpystring.so missing DT_SONAME | Upstream CMakeLists.txt doesn't set SOVERSION | Non-blocking warning, acceptable for library package |

## 源码修改

无补丁文件。所有修改通过 conanfile.py 的 build() 方法中的 CMake CLI 参数处理。

## 依赖版本

无编译依赖（纯 C++ 库，仅依赖标准库）。

## 验证结果

```bash
# Upstream tests (make test)
0 tests failed (17 tests passed)

# CTest
100% tests passed, 0 tests failed out of 1

# Conan test_package
All pystring tests PASSED
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| conanfile.py | ~2KB | Conan 配方 (CMake) |
| conandata.yml | ~280B | 源码 URL + sha256 |
| test_package/test.cpp | ~1KB | 消费者测试 (split, join, strip, upper) |

## 注意事项

- CMakeLists.txt 的 cmake_minimum_required(VERSION 3.2) 是上游代码问题，通过 CMAKE_POLICY_VERSION_MINIMUM 绕过
- CMakeLists.txt 只安装库文件不安装头文件，conanfile.py 中手动 copy pystring.h 到 include/
- 库类型: 静态库 (default_options: shared=False)
---

**编译结束**: 2026-08-29 00:10
**最终状态**: built
<!-- submit-ready -->
