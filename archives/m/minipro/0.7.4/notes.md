# minipro 0.7.4 适配笔记

## 编译环境
- 构建系统: makefile
- 编译日期: 2026-07-16
- 编译器: clang
- 状态: built

## 软件简介

minipro 是 XGecu 系列芯片编程器（TL866CS, TL866A, TL866II+, T48, T56）的开源控制工具。
通过 USB 连接编程器，支持读取、写入、校验 EEPROM、MCU 等可编程器件。

## 构建步骤

```bash
conan create . -pr:h ohos-aarch64 -pr:b ohos-aarch64 --build=minipro/0.7.4
```

## 依赖说明

| 依赖 | 来源 | 提供方式 |
|------|------|---------|
| libusb-1.0 | OpenHarmonyPCDeveloper/cmd-pkgs 项目权威制品源 (1.0.27) | SHA256 校验后静态链接 |
| zlib | Conan Registry (1.3.1) | Conan requirements |

libusb 归档来自 OpenHarmonyPCDeveloper 项目维护的 cmd-pkgs 权威制品渠道，通过 Conan 文件工具执行 TLS 验证、SHA256 校验和安全解压；zlib 声明为 Conan 依赖。

## Makefile 分析

- `CC=gcc` (默认)，可通过 `make CC=clang` 覆盖
- `CFLAGS ?=` 允许环境变量覆盖
- `override CFLAGS += $(libusb_CFLAGS) $(zlib_CFLAGS)` 追加 pkg-config 标志
- `make install` 支持 DESTDIR，安装到:
  - `$(PREFIX)/bin/minipro`
  - `$(PREFIX)/share/man/man1/minipro.1`
  - `$(PREFIX)/share/minipro/infoic.xml`
  - `$(PREFIX)/share/minipro/logicic.xml`
  - udev 规则和 bash-completion (OHOS 不需要)

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | pkg-config 找不到 libusb | CI 环境没有 libusb 开发文件 | 下载并校验 cmd-pkgs 归档，直接传递编译参数 |
| 2 | 需 ELF 签名 | HarmonyOS 要求二进制签名才能执行 | package() 中调用 binary-sign-tool |
| 3 | version.h 生成 | 构建时从 Makefile VERSION 生成 | make 自动处理，无需干预 |

## 验证结果

```bash
$ minipro --version
minipro version 0.7.4     A free and open TL866 series programmer

$ minipro --help
Usage: minipro [options] -p <device>
  ...
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/minipro | 主二进制（已签名） |
| share/man/man1/minipro.1 | 手册页 |
| share/minipro/infoic.xml | 芯片信息数据库 |
| share/minipro/logicic.xml | 逻辑IC测试数据库 |

## 注意事项

1. minipro 是命令行工具，需声明 commands.json (R38)
2. 当前适配仅完成编译和命令行冒烟验证，USB 设备枚举、读写和固件通信尚未验证
3. R40 适配完整性需人工确认：需在 OHOS usb_host 域连接 TL866/T48/T56 实机验证
4. 构建使用 -j1 确保可复现性 (R9)

---

**编译日期**: 2026-07-16
**最终状态**: built
