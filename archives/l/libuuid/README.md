# libuuid

> Universally Unique Identifier library - extracted from util-linux

## 简介

libuuid 提供生成和分析 UUID（Universally Unique Identifier）的功能。UUID 是 128 位的全局唯一标识符，广泛用于分布式系统中的对象标识。

本库从 util-linux 项目提取，只编译 libuuid 组件，避免编译整个 util-linux 工具集。

主要功能：
- **UUID 生成**：生成基于时间、随机数、哈希的 UUID（`uuid_generate*`）
- **UUID 解析**：将字符串转换为 UUID 结构（`uuid_parse`）
- **UUID 格式化**：将 UUID 结构转换为字符串（`uuid_unparse*`）
- **UUID 比较**：比较两个 UUID 是否相同（`uuid_compare`）

## OHOS 适配要点

### 编译建议

只编译 uuid 组件，不编译整个 util-linux：

```bash
./configure \
  --prefix=$HOME/usr/local \
  --disable-all-programs \
  --enable-libuuid
```

### 补丁说明

util-linux 在 HarmonyOS 上编译需处理 configure 临时目录问题：
config.status 创建辅助文件时默认在当前目录（或 umask 077 的私有目录），
HMDFS 上 0700 目录对构建进程不可写。补丁将 ac_tmp 指向 TMPDIR 且不设 0700 权限。

## 排除与替代

不建议编译整个 util-linux，因为：
- 包含大量工具（mount, fdisk, kill 等）
- 许多工具依赖系统特定功能
- 只需要 libuuid 即可满足依赖需求

替代方案：只编译 libuuid 组件。

## 依赖

无外部依赖。
