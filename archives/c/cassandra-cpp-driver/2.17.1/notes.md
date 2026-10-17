# cassandra-cpp-driver 2.17.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-06
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化环境: `ohc-run.py init-build cassandra-cpp-driver 2.17.1 --url=https://github.com/apache/cassandra-cpp-driver/archive/refs/tags/2.17.1.tar.gz`
2. 创建 build 目录: `mkdir -p build && cd build`
3. 执行 cmake 配置:
   ```bash
   cmake .. -DCMAKE_BUILD_TYPE=Release
   ```
4. 编译: `make -j2`
5. 安装: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.8.12) 失败 | CMake 4.1.2 不支持低于 3.5 的版本 | 修改 CMakeLists.txt 第 1 行为 cmake_minimum_required(VERSION 3.5) |
| 2 | 缺少 libuv 依赖 | 项目自定义 FindLibuv.cmake 使用 NO_DEFAULT_PATH 无法找到 Conan 提供的依赖 | 修改 Dependencies.cmake 优先使用 Conan 生成的 find_package(libuv CONFIG) |
| 3 | 缺少 OpenSSL 依赖 | 同 libuv 问题 | 修改 Dependencies.cmake 优先使用 Conan 生成的 find_package(openssl CONFIG) |
| 4 | 缺少 ZLIB 依赖 | 同 libuv 问题 | 修改 Dependencies.cmake 优先使用 Conan 生成的 find_package(zlib CONFIG) |
| 5 | cmake/ClangFormat.cmake cmake_minimum_required 失败 | 同问题 1 | 修改 cmake/ClangFormat.cmake 第 4 行为 cmake_minimum_required(VERSION 3.5) |
| 6 | sparsehash CMakeLists.txt cmake_minimum_required 失败 | 同问题 1 | 修改 src/third_party/sparsehash/CMakeLists.txt 第 1 行为 cmake_minimum_required(VERSION 3.5) |
| 7 | sparsehash hash namespace 检测失败 | CMake check_cxx_source_compiles 在 HarmonyOS 上不工作 | 手动设置 HASH_NAMESPACE=std 和 HASH_FUN_H=functional |
| 8 | uuids.cpp 类型转换警告视为错误 | -Werror + implicit-int-conversion | 修改第 151 行，将整个表达式转换为 char |
| 9 | zlib 静态库无法链接到共享库 | zlib 未编译 -fPIC，无法链接到 libcassandra.so | 改为静态构建 (shared=False)，默认产出 libcassandra_static.a |

## 源码修改

### 补丁文件列表
1. `0001-CMakeLists.txt.patch` - cmake_minimum_required 版本升级
2. `0002-cmake-ClangFormat.cmake.patch` - cmake_minimum_required 版本升级
3. `0003-cmake-Dependencies.cmake.patch` - 使用 Conan 生成的 config 优先发现 libuv/OpenSSL/zlib 依赖
4. `0004-src-third_party-sparsehash-CMakeLists.txt.patch` - cmake_minimum_required 版本升级 + 手动设置 hash namespace
5. `0005-src-uuids.cpp.patch` - 修复类型转换警告

## 依赖版本

- libuv: 1.52.1
- OpenSSL: 3.5.6
- zlib: 1.3.1

## 验证结果

```bash
# 静态库 (默认)
ls -lh lib/libcassandra_static.a
# Conan recipe default_options = {"shared": False}
```

## 交付物

| 文件 | 说明 |
|------|------|
| libcassandra_static.a | 静态库文件 (默认构建) |

## 注意事项

1. cassandra-cpp-driver 使用 CMake 构建系统，不是 autotools
2. 项目有自定义 FindLibuv.cmake 和 FindOpenSSL.cmake，需要通过 patch 使用 Conan 生成的 config
3. 需要在 build 目录中执行 cmake 配置（out-of-source build）
4. sparsehash 的 hash namespace 检测在 HarmonyOS 上不工作，需要手动设置
5. 默认静态构建因 zlib 包未编译 -fPIC，无法链接到共享库

---
**编译结束**: 2026-08-06 03:36
**最终状态**: built
