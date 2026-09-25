# socket

`socket(1)` 把一条 TCP 连接接到标准输入/输出上：既可以作为客户端连接到某个
主机端口，也可以用 `-s` 监听端口当服务端；`-p prog` 则把连接交给一个程序的
stdio（最小化的 netcat/inetd 用法）。

- 上游：Juergen Nickelsen，1992 年发布的 Socket-1.1（原站 ftp.cs.tu-berlin.de 已消失）
- 许可证：GPL-1.0-or-later
- 构建系统：手写 Makefile（shapeTools 风格）
- 依赖：无（仅 libc，POSIX socket API）

## 版本

| 版本 | 状态 | conan ref |
|------|------|-----------|
| 1.1  | built | `socket/1.1` |

## 鸿蒙适配要点

1. `utils.c` 用 BSD `sigvec()` 装信号处理器；OHOS libc 有 `SIG_SETMASK` 宏但
   没有 `struct sigvec`，改为 POSIX `sigaction()`。
2. `globals.h` 的 `extern int errno` 在 errno 为线程局部宏的 libc 上没有符号，
   改为 `#include <errno.h>`。
3. 上游 Makefile 写死 `CC = cc` 并整行覆盖 `CFLAGS`/`LDFLAGS`，且 shapeTools
   的 `+all` 目标会把这些值当命令行变量传给子 make，导致外部注入的交叉编译
   参数全部失效；补丁改为 `?=` / `+=`。
