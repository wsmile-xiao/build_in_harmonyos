# mbelib 1.3.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-28
- 编译器: clang/clang++
- 状态: published

## 编译步骤

```bash
source .build-context-mbelib-1.3.0
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DBUILD_SHARED_LIBS=OFF -DDISABLE_TEST=ON -DCMAKE_POLICY_VERSION_MINIMUM=3.5
make -j2
make install DESTDIR=$TEST_PREFIX
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.6) error | CMake 4.x removed compatibility with < 3.5 | Add -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 2 | Test framework fails (gtest/gmock) | Submodules not present in GitHub archive tarball | Set DISABLE_TEST=ON |
| 3 | GitHub download blocked | Network connectivity to github.com | Used gh-proxy.com mirror for local download; conandata.yml keeps official URL (R39) |

## 源码修改

无源码修改，无补丁。CMakeLists.txt 原生支持 CMake 构建。

## 依赖版本

无外部依赖。mbelib 是纯 C/C++ 库，仅依赖标准数学库 (-lm)。

## 验证结果

```bash
# Build output:
# [100%] Built target mbe-static
# [100%] Built target mbe-shared

# Install output:
# Installing: lib/libmbe.a
# Installing: lib/libmbe.so
# Installing: include/mbelib.h
# Installing: lib/pkgconfig/libmbe.pc
```

## 交付物

| 文件 | 说明 |
|------|------|
| libmbe.a | 静态库 |
| libmbe.so | 共享库 |
| mbelib.h | 公共头文件 |
| libmbe.pc | pkg-config 文件 |

## 注意事项

- 库输出名为 "mbe"（不是 "mbelib"），conanfile.py 中 cpp_info.libs = ["mbe"]
- CMakeLists.txt 同时构建静态和共享目标，配方仅构建所需目标
- 上游无版本标签，使用 master 分支归档，版本号 1.3.0 为约定版本
---

**编译结束**: 2026-08-28 15:10
**最终状态**: built
