# C-Kermit

可脚本化的网络与串口通信软件，用于 UNIX 和 VMS 平台。

## 简介

C-Kermit 是一个集网络和串口通信于一体的软件包，提供统一的、传输无关的、跨平台的方法来实现终端仿真、文件传输、字符集转换和脚本编程。它支持 Kermit 协议、FTP、HTTP、Telnet 等多种网络协议，同时具备串口通信能力。

## 许可证

BSD-3-Clause（简化版三条款 BSD 许可证）

## 版本历史

| 版本 | 状态 | 日期 |
|------|------|------|
| 9.0.302 | built | 2026-06-10 |

## 编译要点 (9.0.302)

- **构建系统**: 手动 Makefile（非 autotools/configure）
- **编译器**: clang 15.0.4
- **依赖**: ncurses 6.4（静态库，--without-shared）
- **关键补丁**:
  - `0002-ckucmd.c.patch`: musl libc FILE 结构不透明，`#ifdef __OHOS__` 守卫用 `conchk()` 替代 `stdin->_cnt`
  - `0003-ckupty.c.patch`: OpenHarmony 缺少 `vhangup` syscall 和 utmp 函数，`#ifdef __OHOS__` 守卫 undef 相关宏
- **关键编译选项**: `-DLINUX -D__OHOS__ -DNOGETUSERSHELL -DCK_NCURSES`
- **适用平台**: OpenHarmony (HongMeng Kernel 1.12.0, aarch64, musl libc)

## 功能特性

- 网络通信: TCP/IP、Telnet、FTP、HTTP
- 串口通信: 支持多种调制解调器
- 文件传输: Kermit 协议、XYZMODEM
- 脚本编程: 支持变量、流程控制、宏定义
- 字符集转换: Latin-1/2、Cyrillic、Greek、Hebrew、Japanese、Unicode