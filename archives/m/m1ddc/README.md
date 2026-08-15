# m1ddc

## 简介

m1ddc 是一个通过 DDC/CI 协议控制外接显示器（亮度、对比度、音量、输入源、色彩增益等）的命令行工具，适用于 Apple Silicon Mac（USB-C / DisplayPort Alt Mode 连接）。适合嵌入脚本自动化控制显示器。

## 功能概述

- `set luminance/contrast/volume/input/red/green/blue n` — 设置显示参数
- `get luminance/contrast/volume/...` — 读取当前值
- `max luminance/contrast/volume/...` — 读取最大值
- `chg luminance/contrast/volume n` — 相对增减
- `display list` / `display n ...` — 显示器枚举与选择（支持 id/uuid/edid/serial 多种标识）

## OHOS 适配

- 上游为 macOS / Apple Silicon 专属工具：m1ddc.m 依赖 `@import Darwin/Foundation/IOKit` 与 Apple 私有 IOAVService 框架（I2C DDC 通道），HarmonyOS PC 无等价公共 API（OHOS clang 报 `module 'Darwin' not found`）。
- 适配方案（patches/0001-portable-nonapple.patch）：m1ddc.m 拆为 `#ifdef __APPLE__` 双路径——原版保留在 Apple 分支，非 Apple 平台编译可移植 C 实现（CLI/帮助文本/VCP 码表与上游一致；无 Apple I2C 传输层时如实报告 "Could not find a suitable external display."，与上游无显示器行为一致）。配方 build() 调用 `apply_conandata_patches` 应用补丁。
- 上游无任何测试套件（归档仅 4 文件），test_package 以可执行文件冒烟测试接入（3 个用例，含真实 DDC 命令的无显示器报告路径）。

## 依赖关系

- 编译依赖：无（仅需 clang）
- 运行依赖：DDC/CI 硬件通道（macOS 私有框架，OHOS 待验证）

## 参考资料

- 官网/源码: https://github.com/waydabber/m1ddc
- License: MIT
