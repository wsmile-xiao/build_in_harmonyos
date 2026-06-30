# fwup

fwup 是一个可配置的基于脚本的嵌入式 Linux 固件更新工具。

## 描述

fwup 用于创建和应用固件更新包。它特别适用于嵌入式设备，支持：
- MBR 和 GPT 分区表
- FAT 文件系统操作
- 签名验证
- 增量更新

## 版本

- **1.16.0** - 最新稳定版本（2026-06-03 编译）

## 依赖

fwup 运行时依赖以下库（需要通过预编译包安装）：
- libarchive (>= 3.7.0)
- libconfuse (>= 2.8)
- lzma (>= 5.6.0)

## 安装

```bash
# 安装依赖
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libarchive 3.7.4
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- libconfuse 3.3
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- lzma 5.6.2

# 安装 fwup
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- fwup 1.16.0
```

## 验证

```bash
fwup --version
# 输出: 1.16.0
```

## 使用

fwup 主要用于嵌入式设备的固件更新，详细使用文档请参考官方文档：
https://github.com/fwup-home/fwup

## 已知问题

1. **动态链接**: fwup 是动态链接的可执行文件，需要预先安装依赖库
2. **HMDFS SELinux**: configure 脚本中的 umask 需要修改（077 -> 022）

## 编译说明

- 构建系统: autotools
- 编译器: clang
- 编译选项: `-march=armv8-a+crypto -O2`
