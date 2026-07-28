# babeld

babeld 是 Babel 路由协议的守护进程实现，一种适用于 mesh 网络和混合网络的路由协议。

## 功能概述

- 实现 Babel 距离向量路由协议（RFC 8966）
- 支持 IPv4 和 IPv6 双栈路由
- 自动检测链路质量，支持有损链路上的高效路由
- 适用于 mesh 网络、无线网络和混合有线/无线网络
- 支持源特定路由（Source-Specific Routing, SADR）
- 内置 BLAKE2s 和 SHA-256 认证支持

## OHOS 适配

### 适配要点

- **纯 Makefile 构建**：babeld 没有使用 Autotools 或 CMake，直接使用 Makefile 编译，需在 Conan 配方中手动处理构建逻辑
- **子模块依赖**：GitHub source archive 不包含 git 子模块内容，需在 `source()` 方法中单独下载 BLAKE2（`BLAKE2/ref/blake2s-ref.c`）和 rfc6234（`reference/sha224-256.c`）
- **rfc6234 仓库迁移**：原始仓库 `massar/rfc6234` 已删除（404），使用 fork `bitpart-xyz/rfc6234`，注意文件在 `reference/` 子目录下，需移动到 `rfc6234/` 目录以匹配 Makefile 路径

### 已知问题

- **sockaddr_storage 重定义**：HarmonyOS 的 `linux/socket.h` 与 `sys/socket.h` 同时定义 `struct sockaddr_storage`，导致编译冲突。解决方案是在 `kernel_netlink.c` 中 `#include <linux/netlink.h>` 之前定义 `_UAPI_LINUX_SOCKET_H`（跳过 `linux/socket.h` 的包含）并补充 `typedef unsigned short __kernel_sa_family_t`
- **LD_LIBRARY_PATH**：编译时需设置 `LD_LIBRARY_PATH` 包含 OHOS SDK 的 `llvm/lib`，否则 `ld.lld` 找不到 `libxml2.so`

## 依赖关系

### 编译依赖

- 无外部库依赖，babeld 是独立二进制
- 子模块源码（非 Conan 依赖，由 `source()` 方法下载）：
  - BLAKE2 — `https://github.com/BLAKE2/BLAKE2`
  - rfc6234 — `https://github.com/bitpart-xyz/rfc6234`（原始仓库 massar/rfc6234 已删除）
- 编译器：clang 15.0 (OHOS SDK)

### 运行依赖

- 仅依赖 `libc.so`

## 参考资料

- 官方仓库：https://github.com/jech/babeld
- Babel 协议规范 (RFC 8966)：https://www.rfc-editor.org/rfc/rfc8966
- Babel 协议主页：https://www.irif.fr/~jch/software/babel/

## 版本列表

| 版本 | 状态 | 编译日期 | Conan 引用 |
|------|------|----------|------------|
| [1.13.1](./1.13.1/) | built | 2026-07-15 | babeld/1.13.1 |
