# batctl

## 简介

batctl (B.A.T.M.A.N. advanced control) 是 Linux 内核 batman-adv (Better Approach To Mobile Ad-hoc Networking - Advanced) mesh 网络协议的用户空间控制工具，提供命令行接口来配置和监控 batman-adv mesh 网络。

主要功能包括：
- Mesh 接口配置（aggregation、bonding、fragmentation 等）
- 调试表访问（originators、neighbors、gateways、transglobal、translocal）
- 网络诊断（ping、traceroute、throughput meter）
- 事件监控
- JSON 查询接口（用于自动化）
- batman-adv 接口上的 TCP dump
- 桥接环路避免（BLA）和分布式 ARP 表（DAT）管理

## OHOS 适配

- **musl/kernel 头文件冲突 (E119)**：`linux/socket.h` 与 `sys/socket.h` 都定义了 `sockaddr_storage`，通过创建 `ohos_compat.h` 头文件，预定义 `_UAPI_LINUX_SOCKET_H` 宏跳过 kernel 头文件，手动提供 `__kernel_sa_family_t` typedef，在 Makefile 中通过 `CFLAGS += -include ohos_compat.h` 引入
- **纯 Makefile 项目**：batctl 不使用 autotools，无 configure 脚本，直接使用 make 构建
- **libnl 系统依赖**：libnl-3.0 和 libnl-genl-3.0 作为系统依赖通过 pkg-config 发现，Conan 配方中动态搜索标准路径并传递给 make
- **内核模块限制**：OpenHarmony 无 batman-adv 内核模块，所有 mesh 命令会报 "module not loaded"，这是平台限制而非编译问题

## 依赖

- libnl-3.0（Netlink 协议库，系统预装共享库 .so）
- libnl-genl-3.0（Generic Netlink 库，系统预装共享库 .so）

## 功能验证

```bash
$ batctl -v
batctl 2025.2 [batman-adv: module not loaded]

$ readelf -d batctl | grep NEEDED
 Shared library: [libnl-3.so.200]
 Shared library: [libnl-genl-3.so.200]
 Shared library: [libc.so]
# libnl 动态链接，运行时需设置 LD_LIBRARY_PATH 指向 libnl 共享库目录

$ readelf -h batctl | grep Type
 Type: DYN (Shared object file)
# PIE + BIND_NOW (RELRO) 安全特性
```

## 参考

- 官网: https://www.open-mesh.org/
- 源码: https://git.open-mesh.org/batctl.git
