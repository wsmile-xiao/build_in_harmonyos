# F3 (Fight Flash Fraud)

## 简介

F3 是一个用于检测闪存卡和 USB 驱动器真实容量的工具。它通过写入测试文件并验证数据完整性来识别假冒存储设备。

## 功能概述

- **f3write**: 向目标驱动器写入测试文件（.h2w），填满标称容量
- **f3read**: 读取并验证 f3write 写入的测试文件，报告真实容量
- **f3probe** (需 libudev): 探测驱动器真实容量
- **f3brew** (需 libudev): 测试驱动器块级读写
- **f3fix** (需 libparted): 在假冒驱动器的可用区域创建分区

## 鸿蒙适配说明

- argp.h 在 HarmonyOS libc 中不可用，需内联构建 argp-standalone 1.5.0
- 仅适配主目标 f3write 和 f3read
- f3probe/f3brew 需要 libudev，f3fix 需要 libparted，当前未适配
