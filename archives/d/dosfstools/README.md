# dosfstools

dosfstools 是一组用于创建和检查 MS-DOS FAT 文件系统的工具。

## 软件简介

dosfstools 包含两个核心工具：

- **mkfs.fat**：在设备或文件上创建 FAT12/FAT16/FAT32 文件系统
- **fsck.fat**：检查和修复 FAT 文件系统上的错误

这些工具是 Linux 系统上管理 FAT 格式存储设备（U盘、SD卡等）的基础工具链。

## 编译版本

| 版本 | 状态 | 日期 |
|------|------|------|
| 4.2 | published | 2026-05-27 |

## 鸿蒙适配要点

- 需修改 config.guess 和 config.sub 以识别 aarch64-ohos 平台三元组
- 纯 C 工具链软件，configure + make 即可编译，无外部依赖
- 二进制安装到 sbin 目录（上游设计）

## 项目主页

https://github.com/dosfstools/dosfstools