# dyad

**轻量级 TCP socket C 库**（单 select 事件循环，来自 rxi/dyad）

dyad 是 rxi（lite 编辑器、microui 作者）的极简 TCP 库：整个库就是两个文件
（`src/dyad.c` + `src/dyad.h`，约 1150 行 C89/C99），围绕一个单线程 select
事件循环组织 TCP 流的监听、连接、读写与生命周期。

## 功能概述

- 流式 API：`dyad_newStream()` 创建流，监听端点或发起连接，事件回调驱动。
- 事件模型：`CONNECT / ACCEPT / DATA / LINE / CLOSE / ERROR / TIMEOUT / TICK /
  READY / LISTEN / DESTROY`，`dyad_addListener()` 注册，`dyad_update()` 泵循环。
- `LINE` 事件按 `\n` 切行并剥 `\r`（行协议友好）；`writef` 支持格式化写出。
- 流计数器：`dyad_getBytesSent / dyad_getBytesReceived`；对端观测：
  `dyad_getAddress / dyad_getPort`。
- 非阻塞全异步：`fcntl O_NONBLOCK` + `select`，单线程即可跑 echo server /
  IRC bot / HTTP server（见上游 example/）。

## 用法

```c
#include "dyad.h"

dyad_init();
dyad_Stream *s = dyad_newStream();
dyad_addListener(s, DYAD_EVENT_ACCEPT, onAccept, NULL);
dyad_listen(s, 8000);
while (dyad_getStreamCount() > 0) { dyad_update(); }
dyad_shutdown();
```

消费方式（Conan）：`requires("dyad/0.0-git.915ae49")`，链接 `dyad::dyad`，
头文件 `#include "dyad.h"`。

## OHOS 适配

- 上游**无构建系统**（仓库仅 src/ + example/ + doc/，example/build.py 只是示例
  辅助脚本）：配方直接用 profile 交叉编译器把 `src/dyad.c` 编成 `dyad.o`，
  `llvm-ar rcs` 归档 `libdyad.a`，`dyad.h` 装入 `include/`。
- 非 Windows 路径纯 POSIX socket API（fcntl / getaddrinfo / select /
  gettimeofday / signal），musl 全兼容，**零补丁、零依赖**（仅 libc）。
- 编译器与归档器从 Conan profile 的 `tools.build:compiler_executables` 字典取
  （R33，同 d52/abc 先例），CI worker 无裸 shell CC 也可复现。
- 源码包 URL 带 ghfast.top 镜像（archive/refs/heads 格式；codeload 格式经
  ghfast 返回 403）+ 官方源兜底；sha256 双源实测一致。
- 上游无测试套件（0 用例）；`test_package` 用 127.0.0.1 socket 回环做消费者
  全链路验证（15 断言：监听/连接/ACCEPT/DATA/LINE/计数器/无泄漏），OHOS 沙箱
  内回环可用，不依赖外网。
- 上游从未发布 release tag；版本号按 git 快照口径 `0.0-git.915ae49`
  （master tip `915ae49`，2016-08-28 最后提交，库内横幅 `DYAD_VERSION "0.2.1"`）。

## 依赖关系

- 编译依赖：无（仅 libc / POSIX socket）
- 运行依赖：无
- 仓库路径：`archives/d/dyad/0.0-git.915ae49/`

## 参考资料

- 源码仓库：https://github.com/rxi/dyad
- 上游文档：源码包内 `doc/api.md`（API 手册）
- 许可证：MIT
