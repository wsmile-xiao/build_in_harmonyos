# dfc for HarmonyOS

## 概述

dfc (Disk Filesystem Checker) 在 HarmonyOS/OpenHarmony (aarch64) 上的预编译包和编译指南。

## 软件信息

| 项目 | 值 |
|------|-----|
| 名称 | dfc |
| 官方描述 | Report file system space usage information with colors and graphs |
| 官方仓库 | https://github.com/rolinh/dfc |
| 许可证 | BSD-3-Clause |

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.1.1 | full | 2 |

## 快速安装

```bash
tar xzf dfc-3.1.1-ohos-aarch64.tar.gz -C ~/usr/local
cd dfc-3.1.1-ohos-aarch64 && sh install.sh
```

## 功能特性

- ✅ 彩色输出和图形显示
- ✅ 多种导出格式（CSV, JSON, HTML, TEXT）
- ✅ inode 信息显示
- ✅ 文件系统过滤和排序
- ✅ 挂载选项显示
- ✅ HarmonyOS 特殊文件系统支持（hmfs, hmdfs, sharefs, erofs）

## 鸿蒙适配说明

dfc 3.1.1 已适配 HarmonyOS/OpenHarmony 系统：

1. **CMakeLists.txt**: 添加 HarmonyOS 平台识别
2. **services-linux.c**: 改进 mtab 文件路径查找兼容性
   - 依次尝试 /etc/mtab, /proc/mounts, /proc/self/mounts
   - 确保 HarmonyOS 系统无 /etc/mtab 时仍能正常工作

## 环境要求

- HarmonyOS/OpenHarmony aarch64
- musl libc (动态链接)

## 相关链接

- [编译指南](./3.1.1/README.md)
- [测试报告](./3.1.1/test-reports/dfc-test-report.md)
- [预编译包](./3.1.1/prebuilt/)