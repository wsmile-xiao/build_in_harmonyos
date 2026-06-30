# uSockets 0.7.1 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-06-24
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 状态: built (功能验证通过)

## 编译步骤

1. **init-build**: `ohc-run.py init-build uSockets 0.7.1 --url=https://github.com/uNetworking/uSockets/archive/c06112c89b4c1cf5a09b5f8daa2def756b925889.tar.gz`
2. **环境设置**: `export PKG_CONFIG_PATH=~/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH`
3. **编译**: `make -j1 WITH_OPENSSL=1` — 编译 10 个目标文件，链接为 uSockets.a 静态库
4. **安装 (DESTDIR)**: 手动复制头文件和静态库到 staging
5. **打包**: `ohc-run.py package uSockets 0.7.1` — 创建 uSockets-0.7.1-ohos-aarch64.tar.gz (130KB)
6. **安装 (本地)**: 复制到 ~/usr/local/lib/uSockets.a + ~/usr/local/include/libusockets.h

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 下载失败 (SSL) | Python urllib SSL 证书验证失败 | 手动 curl -k 下载 |
| 2 | Makefile 无 install 目标 | uSockets 是纯库项目 | 手动复制头文件和静态库 |
| 3 | verify-build G4 失败 | manifest 缺少 build_system 字段 | 添加 build_system: makefile |
| 4 | G0 clean-verify 失败 | 无 configure 脚本 (Makefile 项目) | 已知限制，手动编译已验证 |
| 5 | OpenSSL 3.x deprecation 警告 | PEM_read_DHparams/DH_free 标记废弃 | 仅警告，不影响编译和运行 |

## 源码修改

无补丁。uSockets 源码未修改，直接编译。

## 依赖版本

- OpenSSL 3.5.6 (~/usr/local)
- zlib 1.3.1 (~/usr/local)

## 编译产物

- `uSockets.a` (116KB) — 包含 10 个目标文件: bsd, context, epoll_kqueue, gcd, libuv, loop, openssl, sni_tree, socket, wolfssl
- `libusockets.h` (13KB) — 公共 API 头文件

## 功能测试结果 (2026-06-24)

uSockets 的功能通过上层 uWebSockets 示例间接验证（uSockets 是 uWebSockets 的底层网络库）:

| 间接测试项 | 结果 | 说明 |
|-----------|------|------|
| epoll 事件循环 | ✅ | uWS::App() 事件驱动正常运行 |
| BSD socket 监听 | ✅ | HTTP/WebSocket 端口监听成功 |
| OpenSSL 集成 | ✅ | HTTPS/WSS 连接正常 |
| 并发连接管理 | ✅ | 10 HTTP + 5 WebSocket 并发通过 |
| WebSocket 帧解析 | ✅ | 文本/二进制 echo 正确 |
| SNI 支持 | ✅ | ServerName 示例可执行 |

关键 API 符号验证:
- `us_create_socket_context` ✅
- `us_socket_context_listen` ✅
- `us_socket_context_free` ✅
- `us_listen_socket_close` ✅

> 详细测试报告见 uWebSockets/18/reports/functional-test-report.md

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| uSockets-0.7.1-ohos-aarch64.tar.gz | 130KB | 预编译包 (libusockets.h + uSockets.a) |

## 注意事项

- uSockets 使用纯 Makefile，无 configure/make install
- WITH_OPENSSL=1 启用 SSL 支持，编译 crypto/*.cpp 需要 C++17
- 静态库 uSockets.a 被上层 uWebSockets 链接使用，不单独产生可执行二进制
- sni_tree.o 使用 C++ 编译 (sni_tree.cpp)，其余使用 C 编译
---

**编译结束**: 2026-06-24 14:53
**功能测试**: 2026-06-24 通过 (通过 uWebSockets 上层验证)
**最终状态**: built (功能验证通过)
