# orbuculum

ARM Cortex-M **SWO/SWV (ITM) 追踪采集与后处理工具集**，已适配 HarmonyOS PC (aarch64)。

- 上游：https://github.com/orbcode/orbuculum
- 版本：2.2.0
- 当前包：`archives/o/orbuculum/2.2.0`
- 支持架构：armv8（OHOS 6.0 / clang 15）
- 许可证：GPL-2.0-or-later

## 是什么

orbuculum 从 ARM Cortex-M 目标采集 SWO/SWV 追踪数据（经 orbtrace/BMP 探针、TTL 串口
或文件/套接字流），并围绕共享库 `liborb` 提供一整套后处理工具：

| 工具 | 用途 |
|------|------|
| `orbuculum` | 采集：从探针/串口/流读取 ITM 数据 |
| `orbfifo` | 把采集流转发到 FIFO/文件 |
| `orbcat` | ITM 通道数据转文本/十六进制 |
| `orbtop` | 类似 top 的实时 ITM 统计显示（ncurses） |
| `orbdump` | 转储 ITM 流 |
| `orbstat` | 基于 ELF 符号的统计/分析 |
| `orbmortem` | 崩溃现场分析：ELF+DWARF 源码级回溯（反汇编） |
| `orbprofile` | 剖析输出（开发预览） |
| `orbtrace` | orbtrace 硬件控制 |
| `orbzmq` | ZMQ 接口 |
| `orblcd` | ITM 通道 LCD/图形显示（SDL2） |

## 依赖（全部来自 OHOS Conan 制品仓）

`libusb/1.0.27`、`libzmq/4.3.5`、`ncurses/6.6`（静态）、`libelf/0.8.13.1`、
`libdwarf/0.11.1`、`capstone/5.0.7`、`sdl2/2.32.10`（+ 传递 `zlib/1.3.1`、`zstd/1.5.6`）。

## 适配要点（详见 2.2.0/notes.md）

1. 上游 meson 通过 wrap subproject 在 configure 期联网下载 libdwarf；
   本配方改用 Conan 依赖 `dependency('libdwarf')`，构建完全离线。
2. OHOS 无 `asm/ioctls.h`、`asm/termios.h` 与 `linux/tcp.h`，改用 `asm-generic/*`
   通用头并移除无用包含。
3. libusb/capstone 的包含路径改为 `<libusb.h>` / `<capstone/capstone.h>`。
4. libdwarf 静态链接的 `_dwarf_error` 符号冲突 → 删除上游死代码。
5. 上游 `Tests/test_cobs.c` 已陈旧（API 漂移），最小化修补后在 `build()` 中编译执行。

## 验证

- 上游测试 `Tests/test_cobs.c`：33/33 OK + 10000 次随机往返压力，0 失败。
- 消费者测试：`test_orb.c`（liborb COBS API）8/8；`test.sh` 11/11 工具安装、10/10 版本正确。
