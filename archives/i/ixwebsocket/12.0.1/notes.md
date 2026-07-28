# ixwebsocket 12.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-22
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

1. `conan install . --build=missing -pr:h=$HOME/.conan2/profiles/default -pr:b=$HOME/.conan2/profiles/default` — 安装依赖 zlib/1.3.1, openssl/3.5.6，生成 CMakeToolchain 和 CMakeDeps
2. `cmake -B build -DCMAKE_TOOLCHAIN_FILE=<conan_toolchain> -DCMAKE_BUILD_TYPE=Release -DUSE_TLS=1 -DUSE_ZLIB=1 -DUSE_WS=OFF -DUSE_TEST=OFF -DBUILD_DEMO=OFF -DCMAKE_INSTALL_PREFIX=$TEST_PREFIX` — CMake 配置
3. `cmake --build build -j2` — 编译，生成 libixwebsocket.a 静态库
4. `cmake --install build --prefix $TEST_PREFIX` — 安装到测试前缀

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 配置时 ZLIB::ZLIB target not found | Conan CMakeDeps 生成小写目标名 zlib::zlib，而 CMakeLists.txt 使用大写 ZLIB::ZLIB（CMake 内置 FindZLIB 模块目标） | 补丁 0001-cmake-conan-targets.patch 修改 CMakeLists.txt 使用 conan 目标名 |
| 2 | OpenSSL 链接失败 (${OPENSSL_LIBRARIES} 为空) | Conan CMakeDeps 设置 openssl_LIBRARIES（小写），而 CMakeLists.txt 使用 OPENSSL_LIBRARIES（大写） | 同上补丁，改用 openssl::openssl target |
| 3 | ctest 无测试可用 | USE_TEST=OFF 禁用了测试构建（测试需要 spdlog FetchContent 网络下载） | 记录为已知限制，conan recipe 中禁用测试 |

## 源码修改

补丁文件: `patches/0001-cmake-conan-targets.patch`
- 将 `find_package(ZLIB REQUIRED)` 改为 `find_package(zlib REQUIRED)`
- 将 `ZLIB::ZLIB` 改为 `zlib::zlib`
- 将 `find_package(OpenSSL REQUIRED)` 改为 `find_package(openssl REQUIRED)`
- 将 `${OPENSSL_LIBRARIES}` 改为 `openssl::openssl` target
- 移除 `${OPENSSL_INCLUDE_DIR}` include 目录（由 conan target 处理）

## 依赖版本

| 依赖 | 版本 | 来源 |
|------|------|------|
| zlib | 1.3.1 | ohpcd 制品仓 |
| openssl | 3.5.6 | ohpcd 制品仓 |
| spdlog | (bundled, 未使用) | IXWebSocket third_party/ (仅 USE_WS/USE_TEST 时需要) |

## 验证结果

```bash
# 构建产物验证
$ file libixwebsocket.a
libixwebsocket.a: ar archive

$ llvm-readelf -a libixwebsocket.a | grep Machine
Machine: AArch64

# test_package 验证
$ cmake --build . && ctest
IXWebSocket version: 11.4.6
IXWebSocket URL parser test passed!
```

## 注意事项

- IXWebSocket 使用 CMake 构建系统，非 autotools
- 默认构建静态库 (BUILD_SHARED_LIBS=OFF)
- TLS 默认使用 OpenSSL 后端
- spdlog 通过 FetchContent 从网络下载，仅在构建 ws 工具或测试时需要，conan recipe 中已禁用
- IX_WEBSOCKET_VERSION 为 "11.4.6"（上游版本号定义，与 tag v12.0.1 不同，这是上游的版本命名习惯）
---

**编译结束**: 2026-07-22 10:22
**最终状态**: built
