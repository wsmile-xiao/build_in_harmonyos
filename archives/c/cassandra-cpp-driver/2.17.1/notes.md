# cassandra-cpp-driver 2.17.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-02
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化环境: `ohc-run.py init-build cassandra-cpp-driver 2.17.1 --url=https://github.com/apache/cassandra-cpp-driver/archive/refs/tags/2.17.1.tar.gz`
2. 创建 build 目录: `mkdir -p build && cd build`
3. 执行 cmake 配置:
   ```bash
   export PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig
   export LIBUV_ROOT_DIR=/storage/Users/currentUser/usr/local
   export OPENSSL_ROOT_DIR=/storage/Users/currentUser/usr/local
   export ZLIB_ROOT_DIR=/storage/Users/currentUser/usr/local
   cmake .. -DCMAKE_INSTALL_PREFIX=/storage/Users/currentUser/usr/local
   ```
4. 编译: `make -j2`
5. 安装（staging）: `make install DESTDIR=/storage/Users/currentUser/test-install-cassandra-cpp-driver-2.17.1`
6. 安装（本地）: `make install`

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake_minimum_required(VERSION 2.8.12) 失败 | CMake 4.1.2 不支持低于 3.5 的版本 | 修改 CMakeLists.txt 第 1 行为 cmake_minimum_required(VERSION 3.5) |
| 2 | 缺少 libuv 依赖 | 未设置 PKG_CONFIG_PATH 和 LIBUV_ROOT_DIR | export PKG_CONFIG_PATH + export LIBUV_ROOT_DIR=/storage/Users/currentUser/usr/local |
| 3 | 缺少 OpenSSL 依赖 | 未设置 OPENSSL_ROOT_DIR | export OPENSSL_ROOT_DIR=/storage/Users/currentUser/usr/local |
| 4 | 缺少 ZLIB 依赖（警告） | 未设置 ZLIB_ROOT_DIR | export ZLIB_ROOT_DIR=/storage/Users/currentUser/usr/local |
| 5 | cmake/ClangFormat.cmake cmake_minimum_required 失败 | 同问题 1 | 修改 cmake/ClangFormat.cmake 第 4 行为 cmake_minimum_required(VERSION 3.5) |
| 6 | sparsehash CMakeLists.txt cmake_minimum_required 失败 | 同问题 1 | 修改 src/third_party/sparsehash/CMakeLists.txt 第 1 行为 cmake_minimum_required(VERSION 3.5) |
| 7 | sparsehash hash namespace 检测失败 | CMake check_cxx_source_compiles 在 HarmonyOS 上不工作 | 手动设置 HASH_NAMESPACE=std 和 HASH_FUN_H=functional |
| 8 | uuids.cpp 类型转换警告视为错误 | -Werror + implicit-int-conversion | 修改第 151 行，将整个表达式转换为 char |

## 源码修改

### 补丁文件列表
1. `0001-CMakeLists.txt.patch` - cmake_minimum_required 版本升级
2. `0002-cmake-ClangFormat.cmake.patch` - cmake_minimum_required 版本升级
3. `0003-src-third_party-sparsehash-CMakeLists.txt.patch` - cmake_minimum_required 版本升级 + 手动设置 hash namespace
4. `0004-src-uuids.cpp.patch` - 修复类型转换警告

## 依赖版本

- libuv: 1.52.1
- OpenSSL: 3.0.13
- zlib: 1.3.1

## 验证结果

```bash
ls -lh /storage/Users/currentUser/usr/local/lib/libcassandra.so
# -rwxrwx--- 1 20001006 file_manager 3.3M 2026-06-02 12:53 libcassandra.so
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libcassandra.so | 3.3M | 共享库文件 |

## 注意事项

1. cassandra-cpp-driver 使用 CMake 构建系统，不是 autotools
2. 必须设置环境变量 PKG_CONFIG_PATH、LIBUV_ROOT_DIR、OPENSSL_ROOT_DIR、ZLIB_ROOT_DIR
3. 需要在 build 目录中执行 cmake 配置（out-of-source build）
4. sparsehash 的 hash namespace 检测在 HarmonyOS 上不工作，需要手动设置

---
**编译结束**: 2026-06-02 12:54
**最终状态**: built