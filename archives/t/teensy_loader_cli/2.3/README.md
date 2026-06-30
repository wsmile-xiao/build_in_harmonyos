# teensy_loader_cli 2.3 — OHOS AArch64 预编译包

Command line interface for uploading firmware to Teensy USB development boards.

## 概述

teensy_loader_cli 是 PJRC 提供的命令行工具，用于通过 USB 将固件 (.hex) 上传到 Teensy 开发板。
本预编译包为 OpenHarmony (OHOS) AArch64 平台编译，静态链接 libusb-1.0 以确保在 OHOS 上可靠运行。

## 源码信息

- **上游**: https://github.com/PaulStoffregen/teensy_loader_cli
- **版本**: 2.3
- **许可证**: GPL-3.0-only
- **语言**: C
- **构建系统**: 纯 Makefile（无 autotools）

## 编译配置

| 项 | 值 |
|---|---|
| 编译器 | clang 15.0.4 |
| 目标平台 | AArch64 (ELF64 PIE) |
| 链接方式 | 静态链接 libusb-1.0.a，动态链接 libc.so |
| 编译选项 | -fPIC -O2 |
| PREFIX | ~/usr/local |

## 依赖

- **libusb 1.0.27** (静态链接) — OHOS 上 LD_LIBRARY_PATH 不可靠，必须静态链接

## 补丁

| # | 补丁 | 说明 |
|---|------|------|
| 0001 | Makefile.patch | CC=clang, -fPIC, 静态链接 libusb-1.0.a, -include config.mk, install target |
| 0002 | configure.patch | 新增 dummy configure 脚本（处理 --prefix，生成 config.mk） |
| 0003 | teensy_loader_cli.c.patch | libusb-0.1 API → libusb 1.0 API 移植 |

所有补丁为平台适配性质 (platform_only)，不影响上游功能逻辑。

## 使用方法

```bash
# 解压
tar xzf teensy_loader_cli-2.3-ohos-aarch64.tar.gz

# 查看支持的 MCU
./bin/teensy_loader_cli --list-mcus

# 上传固件
./bin/teensy_loader_cli --mcu=imxrt1062 -w firmware.hex
```

## 支持的 MCU 列表

| 短名 | 全名 |
|------|------|
| at90usb162 | AT90USB162 |
| atmega32u4 | ATmega32U4 |
| at90usb646 | AT90USB646 |
| at90usb1286 | AT90USB1286 |
| mkl26z64 | MKL26Z64 (Teensy LC) |
| mk20dx128 | MK20DX128 (Teensy 3.0) |
| mk20dx256 | MK20DX256 (Teensy 3.1/3.2) |
| mk66fx1m0 | MK66FX1M0 (Teensy 3.6) |
| mk64fx512 | MK64FX512 (Teensy 3.5) |
| imxrt1062 | IMXRT1062 (Teensy 4.0/4.1) |

别名: TEENSY2, TEENSY2PP, TEENSYLC, TEENSY30, TEENSY31, TEENSY32, TEENSY35, TEENSY36, TEENSY40, TEENSY41, TEENSY_MICROMOD

## 命令选项

```
Usage: teensy_loader_cli --mcu=<MCU> [-w] [-h] [-n] [-b] [-v] <file.hex>
	-w : Wait for device to appear
	-r : Use hard reboot if device not online
	-s : Use soft reboot if device not online (Teensy 3.x & 4.x)
	-n : No reboot after programming
	-b : Boot only, do not program
	-v : Verbose output
```

## 构建说明

```bash
./configure --prefix=$DEFAULT_PREFIX
make -j1
make install DESTDIR=$STAGING_DIR
```

注意: configure 是 dummy 脚本（纯 Makefile 项目无 autotools），仅处理 --prefix 参数。

## 已知限制

- 无 `--version` 选项（上游不支持）
- USB 设备操作需要 root 权限或 udev 规则配置
- 仅支持 .hex 格式固件文件

## 测试报告

详见 `reports/test-report.md` — 17 项验证全部 PASS。

## 知识沉淀

1. 纯 Makefile 项目需 dummy configure + install target 补丁（E105 模式）
2. OHOS LD_LIBRARY_PATH 不可靠 → libusb 必须静态链接
3. 源码使用旧版 libusb-0.1 API → 需移植到 libusb 1.0 API
4. OHOS /bin/sh 不支持 heredoc → configure 脚本用 echo 替代
5. manifest.yaml configure_options 必须用平面字符串格式