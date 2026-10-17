# linux-firmware-brcm 20260622 — 适配笔记

## 概述
首次将 linux-firmware-brcm（Broadcom brcm 固件资源包子集）适配到 OHOS Conan 包管理。

## 适配方案
- **类型**: 纯固件资源包（firmware-resource-package）
- **模式**: Conan resource package, package_type = "unknown"
- **源**: 从 kernel.org 官方 linux-firmware-20260622.tar.xz 提取 brcm/ 子目录
- **编译**: 无（build() 空）
- **打包**: package() 将 brcm/ 复制到 res/brcm/
- **测试**: test_package 通过 shell 脚本验证 25 项资源断言

## 文件清单
brcm/ 目录共 56 个文件：
- 23 个 .bin 固件二进制
- 2 个 .fw 固件
- 1 个 .hcd USB 蓝牙固件
- 30 个 .txt 板级配置文件
- 0 个 ELF/可执行文件

## 经验教训
1. linux-firmware 完整 tarball 较大 (.tar.gz 950MB / .tar.xz 639MB)，
   推荐使用 .tar.xz 减少下载量。
2. 部分 brcm 固件是到 cypress/ 的软链接，package() 需处理。
3. 厂商板名文件包含空格/括号，是合法的上游文件名。

## 许可证
LICENCE.broadcom_bcm43xx — Broadcom 专有许可，允许再分发

## 路径 B 说明
新增 knowledge/graph/draft/firmware-resource-package-brcm-validation.kv，
可复用到其他 linux-firmware 子包（iwlwifi, ath10k, rtlwifi 等）。
---

**编译结束**: 2026-07-30 18:16
**最终状态**: built
