# grpc 1.70.0 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-27
- 编译器: clang/clang++ (Clang 15.0.4, OHOS SDK 26.0.0.18)
- 状态: published

## 背景

recc (BuildGrid/buildbox 1.4.13) 硬依赖 gRPC（buildbox-common `find_package(gRPC 1.30) REQUIRED`）。
制品仓无 grpc 可用包：1.49.2 与制品仓 protobuf/33.6 API 不兼容（protobuf 33 移除了
`util::Status` 与 `csharp_names.h`），本地实测编译失败，否决。改用 gRPC 1.70.0。

## 编译步骤

```bash
conan create . --profile=ohos-aarch64 --build=missing
```

配方 generate() 关键设置：
- 全部依赖走制品仓：gRPC_{ABSL,CARES,PROTOBUF,RE2,SSL,ZLIB}_PROVIDER=package
- 只构建 C++ 插件：gRPC_BUILD_GRPC_CPP_PLUGIN=ON，其余语言插件 OFF
- 显式指定依赖 config：Protobuf_DIR / utf8_range_DIR / absl_DIR / OPENSSL_ROOT_DIR
- 构建目录改名：cmake_layout(build_folder="cmake-build")（见问题 2）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | OHOS 无 pthread_cancel（thd.cc Thread::Kill 编译失败） | musl 未提供 pthread_cancel | 0001 补丁：`#if !defined(GPR_ANDROID) && !defined(__OHOS__)` 走 no-op 分支 |
| 2 | `NotADirectoryError: .../b/build/Release` | grpc 源码根目录有名为 `build` 的文件（Bazel BUILD），与 cmake_layout 默认 `build/` 目录冲突 | `cmake_layout(self, build_folder="cmake-build")` |
| 3 | `find_package(Protobuf)` 找不到 config | protobuf 配方 cmake_find_mode=none，CMakeDeps 不生成其 config | 显式设置 Protobuf_DIR / utf8_range_DIR / absl_DIR 指向包内 config |
| 4 | node_plugin.cc 编译失败（GetJSServiceFilename absl::string_view → std::string） | grpc 1.70.0 语言插件与新版 absl 不兼容 | 只构建 C++ 插件，其余插件 OFF |
| 5 | test_package 链接报 deflateEnd 未定义 | libgrpc.a 引用 zlib 符号，但 gRPCConfig 不传播 zlib | test_package 显式 find_package(zlib CONFIG) + 链接 zlib::zlib |
| 6 | gitee 镜像下 conan 下载 sha256 不匹配 | gitee 对 Conan UA 返回 HTML 页面而非 tarball | conandata URL 改用 GitHub 官方源（R39） |
| 7 | absl ABI 冲突 | grpc 默认找 lts_20240722，与 protobuf 的 lts_20260107 冲突 | 统一用 abseil-cpp/20260107.1，0002 补丁别名 absl::absl → abseil-cpp::abseil-cpp |
| 8 | c-ares / OpenSSL target 名不匹配 | CMakeDeps 导出 c-ares::c-ares / openssl::openssl，grpc 期望 c-ares::cares / OpenSSL::SSL | 0003/0004 补丁接受制品仓 target 名 |

## 源码修改

- 0001-thd-pthread-cancel.patch：src/core/util/posix/thd.cc，OHOS 下 Thread::Kill 走 no-op
- 0002-abseil-cpp-cmake-alias.patch：cmake/abseil-cpp.cmake，absL 组件别名到 abseil-cpp
- 0003-cares-cmake-target.patch：cmake/cares.cmake，接受 c-ares::c-ares
- 0004-ssl-cmake-target.patch：cmake/ssl.cmake，接受 openssl::openssl

## 依赖版本

- abseil-cpp/20260107.1（与 protobuf ABI 一致）
- protobuf/33.6
- c-ares/1.34.6
- re2/2024-04-01
- openssl/3.5.6
- zlib/1.3.1

## 验证结果

```bash
conan create . --profile=ohos-aarch64 --build=missing
# grpc/1.70.0 编译通过（0 error），test_package test_grpc 通过
# 1/1 Test #1: test_grpc  Passed  0.12 sec（100% 通过）
```
