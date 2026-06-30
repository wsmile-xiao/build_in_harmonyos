# minicom 2.10 - OpenHarmony 发布说明

**发布日期:** 2026-05-16
**版本:** 2.10
**平台:** OpenHarmony aarch64
**状态:** 完整 (所有程序已完成编译)

## 概述

minicom 是一个流行的终端通信程序，类似于 Telix 但更适合 Unix/Linux 环境。本次发布将 minicom 2.10 完整适配到 OpenHarmony 平台，包含全部 4 个程序。

## 包含程序

| 程序 | 大小 | 功能 |
|------|------|------|
| minicom | 530KB | 串口终端主程序 |
| ascii-xfr | 35KB | ASCII 文件传输工具 |
| minicom_keyserv | 55KB | 键盘服务进程 |
| runscript | 76KB | 自动化脚本执行器 |

## 功能特性

- 串口终端通信
- 支持多种波特率
- ANSI/VT100 终端仿真
- ASCII 文件传输协议
- 脚本自动化功能
- 配置文件管理
- 键盘按键翻译服务

## 安装

```bash
# 使用安装脚本
./install-minicom-2.10.sh

# 或手动解压
tar -xzf minicom-2.10-ohos-aarch64.tar.gz -C /
```

## 使用方法

```bash
# 启动 minicom
minicom -D /dev/ttyUSB0 -b 115200

# 进入设置模式
minicom -s

# 传输文件
ascii-xfr -s filename

# 执行脚本
runscript scriptfile
```

## 平台适配说明

### 主要修改

1. **构建系统适配**
   - 添加 `--build=aarch64-linux-gnu` 配置参数
   - 指定锁目录路径
   - 修复 config.status 临时目录权限问题

2. **依赖处理**
   - 使用系统 libtinfo.so.6 替代 ncurses
   - 启用 HAVE_TERMCAP_H 定义
   - 修复 termcap.h 模板变量

3. **源码修改**
   - 修正 libport.h 引用路径
   - 在 main.c 定义全局变量 (LINES, COLS, program_name)
   - 在 keyserv.c 定义独立全局变量
   - 在 script.c 定义 program_name

### 补丁列表

| 补丁 | 描述 |
|------|------|
| 0001-patch-ai-review.txt.patch | AI 审核记录 |
| 0002-main.c.patch | main.c 源码修改 |
| 0003-po-Makefile.in.patch | po 目录构建修复 |
| 0004-src-keyserv.c.patch | keyserv 全局变量定义 |
| 0005-src-main.c.patch | main.c 全局变量定义 |
| 0006-src-script.c.patch | script.c 全局变量定义 |
| 0007-minicom.spec.patch | spec 文件更新 |
| 0008-missing-aclocal.patch | aclocal 缺失处理 |
| 0009-po-POTFILES.patch | POTFILES 更新 |
| 0010-src-minicom.h.patch | libport.h 路径修复 |

## 测试结果

- 版本信息: ✅ 通过
- 帮助信息: ✅ 通过  
- 二进制格式: ✅ 通过 (ELF 64-bit aarch64)
- 质量门禁 G1-G4: ✅ 全部通过

## 依赖信息

- **运行时:** libtinfo.so.6 (已打包)
- **编译时:** clang 15.0.4, make 4.4.1, autoconf 2.72, automake 1.16.5

## 文件清单

```
minicom-2.10-ohos-aarch64.tar.gz       - 主程序包 (755KB)
minicom-2.10-ohos-aarch64-debug.tar.gz - 调试符号包 (520KB)
install-minicom-2.10.sh                - 安装脚本
```

## 参考链接

- upstream: https://salsa.debian.org/minicom-team/minicom