# openocd 0.12.0 — Conan 配方

## 适配概述

OpenOCD（Open On-Chip Debugger）是用于 JTAG/SWD 调试和 Flash 编程的
开源命令行工具。

## 构建系统

- Autotools（configure + make）
- 使用 SourceForge 官方 release tarball：自带预生成 configure，
  且打包了 jimtcl/libjaylink 子模块源码，无需 autoreconf

## 配置选项

- `--disable-werror` — 避免新编译器告警导致构建失败
- `--disable-internal-libjaylink` — 禁用内部 libjaylink 子模块
- `--disable-doxygen-*` — 禁用文档生成（减少构建时间与依赖）

## 依赖

- 无外部 Conan 依赖；USB 适配器驱动（libusb/hidapi/libftdi）均为可选，
  在 OHOS 沙箱中未启用
