# lm4tools

## 简介

lm4tools 是 TI Stellaris / Tiva C LaunchPad 开发板的官方配套开源工具集
（utzig 维护的社区延续版），包含两个基于 libusb-1.0 的命令行工具：
`lm4flash` 固件烧写器与 `lmicdi` GDB-USB 调试桥。

## 功能概述

- `lm4flash`：把二进制固件镜像经 USB 写入 LaunchPad 板载 ICDI 调试器
  - `-V` 版本、`-h` 用法、`-v` 烧写后校验、`-E` 只擦除将写入的块
  - `-S address` 指定写入起始地址（十六进制，须按 1024 字节擦除块对齐）
  - `-s SERIAL` 多板连接时按序列号选择目标板
- `lmicdi`：把板载 ICDI 暴露为 GDB 远程调试服务（无参数，直接枚举 USB 设备）

## OHOS 适配

### 0.1.3（feat/lm4tools-0.1.3）

- 构建系统是两个独立的手写 Makefile（`lm4flash/` 与 `lmicdiusb/`，无
  configure / CMake / meson，无顶层统一入口），各自产出一个 CLI
- 两个 Makefile 都按 `uname` 分支（Linux/Darwin/FreeBSD）选择 libusb 的
  链接规则：`lmicdiusb` 用 `ifeq ($(shell uname),...)` 三分支，`lm4flash`
  默认走 `pkg-config`。鸿蒙 `uname -s` 返回 `HarmonyOS`，全部分支落空，
  libusb 变量为空 → 链接 undefined reference。解法是 make 命令行显式注入
  `LIBUSB_CFLAGS/LIBUSB_LIBDIR/LIBUSB_LIBS`（lmicdiusb）与
  `CFLAGS/LDFLAGS`（lm4flash），零补丁
- libusb 取自 conan 包 `libusb/1.0.27`（OHOS AArch64），用依赖 cpp_info
  直接拼 `-I/-L` 路径；包内 `libusb-1.0.pc` 的 prefix 未重定位（指向
  /usr/local），不可信
- **tarball 内 `lm4flash/bin/` 与 `lmicdiusb/bin/` 提交了预编译的外来 ABI
  二进制**：构建前删除，避免 make 判定"目标已最新"跳过重链、或把无法在
  鸿蒙上执行的产物打进包
- 上游无测试套件（两个 Makefile 均无 `check`/`test` 目标，无 tests/ 树），
  由 `test_package` 补全 22 项独立检查：功能 13 项（F1-F13）+ 鸿蒙特有
  9 项（A1-A9，纯 Python 解析 ELF，交叉编译机上也能实跑）
- 命令行工具，已按 R38 声明 `commands.json`
- **硬件边界**：`lm4flash` 的烧写/校验与 `lmicdi` 的调试会话需要真实
  Stellaris LaunchPad ICDI 板（USB VID:PID 1cbe:00fd）。无设备环境只能
  验证"可执行文件/链接/参数解析"与"无设备时干净失败"，不伪造硬件通过结果

## 依赖关系

- 编译依赖：`libusb/1.0.27`（conan，OHOS AArch64）、clang、make
- 运行时依赖：鸿蒙 musl `libc.so` + `libusb-1.0.so.0`（DT_NEEDED 恰为两者）
- 硬件（使用时）：Stellaris LaunchPad ICDI 调试器（USB 1cbe:00fd）

## 参考资料

- 上游仓库：<https://github.com/utzig/lm4tools>
- TI Stellaris LaunchPad：<https://www.ti.com/tool/EK-LM4F120XL>
