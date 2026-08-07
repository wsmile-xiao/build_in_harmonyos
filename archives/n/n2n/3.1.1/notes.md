# n2n 3.1.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-28
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

使用 CMake 构建（autotools 需要运行 autoreconf 且 config.guess 需打补丁，CMake 更简单）：

```bash
cd $BUILD_SRC_DIR && mkdir -p build && cd build
PKG_CONFIG_PATH=/storage/Users/currentUser/usr/local/lib/pkgconfig cmake \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_C_COMPILER=clang \
  -DCMAKE_CXX_COMPILER=clang++ \
  -DN2N_OPTION_USE_OPENSSL=ON \
  -DN2N_OPTION_USE_PTHREAD=OFF \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_POLICY_VERSION_MINIMUM=3.5 \
  ..
make -j1
make install DESTDIR=$TEST_PREFIX
```

注意：
- CMake 版本兼容性问题：n2n 3.1.1 使用 cmake_minimum_required(VERSION 2.6)，需要 -DCMAKE_POLICY_VERSION_MINIMUM=3.5
- N2N_OPTION_USE_PTHREAD=OFF：因为 musl/OHOS 不支持 pthread_cancel，n2n 的线程函数使用 pthread_cancel 来终止无限循环线程，无法简单替换
- N2N_OPTION_USE_OPENSSL=ON：使用 OpenSSL 1.1.1w 提供加密支持

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | sockaddr_storage 重定义错误 | OHOS 上 linux/socket.h（被 linux/netlink.h 包含）和 sys/socket.h 都定义了 sockaddr_storage，导致编译冲突 | 在 n2n.h 中用 #ifndef __OHOS__ 守卫 linux/netlink.h/rtnetlink.h/if_tun.h 的包含 |
| 2 | netlink 路由代码编译失败 | OHOS 不提供完整的 linux/netlink.h/rtnetlink.h API | 在 edge_utils.c 中用 #if defined(__linux__) && !defined(__OHOS__) 守卫所有 netlink 路由代码 |
| 3 | tuntap_linux.c 编译失败 | OHOS 不支持 TUN/TAP 设备（/dev/net/tun）和 netlink socket | 在 tuntap_linux.c 中添加 __OHOS__ stub 函数（tuntap_open 返回 -1，读写返回 0） |
| 4 | CMake 版本兼容性 | n2n cmake_minimum_required(VERSION 2.6) 与 CMake 4.1.2 不兼容 | 添加 -DCMAKE_POLICY_VERSION_MINIMUM=3.5 |
| 5 | pthread_cancel 不可用 | musl/OHOS 不实现 pthread_cancel | 禁用 pthread（N2N_OPTION_USE_PTHREAD=OFF） |

## 源码修改

| 文件 | 修改内容 | 补丁状态 |
|------|----------|----------|
| include/n2n.h | 添加 #ifndef __OHOS__ 守卫排除 linux/netlink.h/rtnetlink.h/if_tun.h | 待生成 |
| src/tuntap_linux.c | 添加 __OHOS__ stub 函数块（tuntap_open/read/write/close/get_address） | 待生成 |
| src/edge_utils.c | 将 4 处 #ifdef __linux__ 改为 #if defined(__linux__) && !defined(__OHOS__) | 待生成 |

## 依赖版本

- OpenSSL: 1.1.1w (预编译包)
- musl libc: OHOS 内置

## 验证结果

```bash
$ /storage/Users/currentUser/usr/local/sbin/edge
Welcome to n2n v.3.1.1 for HarmonyOS
Built on May 28 2026 23:49:51

$ /storage/Users/currentUser/usr/local/sbin/supernode
Welcome to n2n v.3.1.1 for HarmonyOS

$ file edge supernode
ELF shared object, 64-bit LSB arm64, dynamic (/lib/ld-musl-aarch64.so.1)

$ readelf -d edge | grep NEEDED
libssl.so.1.1, libcrypto.so.1.1, libc.so

# 测试结果
tests-auth: PASS
tests-compress: PASS
tests-elliptic: PASS
tests-hashing: PASS
tests-transform: PASS
tests-wire: PASS
```

## 注意事项

1. **Edge (VPN客户端) 功能受限**：由于 OHOS 不支持 TUN/TAP 设备，edge 的 tuntap_open 会返回错误，VPN 隧道功能无法使用。但 edge 仍可编译运行。
2. **Supernode (VPN协调服务器) 完全可用**：supernode 不依赖 TUN/TAP，可正常作为 P2P VPN 的协调节点运行。
3. **路由管理不可用**：netlink 路由 API 在 OHOS 上不可用，路由设置/清理功能被 stub 处理。
4. **pthread 功能禁用**：DNS 解析和端口映射的多线程功能不可用（N2N_OPTION_USE_PTHREAD=OFF）。
5. **OpenSSL 加密可用**：AES/ChaCha20 等加密功能正常工作。
---

**编译结束**: 2026-08-07 04:33
**最终状态**: built
