# nng — nanomsg-next-generation 轻量级消息库

## 简介

nng (nanomsg-next-generation) 是 nanomsg 的重新实现，提供轻量级、高性能的消息通信能力。它是纯 C 实现，无外部依赖，适合嵌入式和资源受限场景。

支持的通信协议：
- **BUS** — 组播（多对多）
- **PAIR** — 双向一对一通信（v0/v1 两个版本）
- **PUSH/PULL** — 单向管道（负载均衡）
- **PUB/SUB** — 发布订阅（支持 xpub/xsub 代理）
- **REQ/REP** — 请求回复（支持 xreq/xrep 代理）
- **SURVEY** — 问卷调查（支持 xsurvey/xrespond 代理）

支持的传输方式：
- inproc（进程内）、IPC（进程间）、TCP、TLS、WebSocket

## 已编译版本

| 版本 | 状态 | 构建系统 | 日期 |
|------|------|----------|------|
| 1.11 | published | cmake | 2026-06-11 |

## 编译配置

- 编译器：clang 15.0.4 / clang++ 15.0.4
- 平台：HarmonyOS (aarch64)
- cmake 选项：`-DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`
- 无外部依赖

## 安装产物

- `lib/libnng.a` — 静态链接库
- `bin/nngcat` — 命令行调试/测试工具
- `lib/cmake/nng/nng-config.cmake` — CMake 查找模块
- `lib/cmake/nng/nng-config-version.cmake` — 版本信息
- `include/nng/*.h` — 头文件（35 个）

## 使用方式

```cmake
# CMakeLists.txt
find_package(nng REQUIRED)
target_link_libraries(myapp nng)
```

```c
// C 代码
#include <nng/nng.h>

nng_socket sock;
nng_pair1_open(&sock);
nng_listen(sock, "tcp://127.0.0.1:5555", NULL, 0);
```

## 平台注意事项

- nng 不提供 pkg-config (.pc) 文件，使用 CMake config 文件替代
- IPC (Unix Domain Socket) listener 在鸿蒙平台受权限限制，建议使用 TCP 或 inproc 传输替代