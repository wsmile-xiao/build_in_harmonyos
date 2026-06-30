# sleuthkit

## 简介

sleuthkit（The Sleuth Kit）是一套开源的数字取证工具集，用于分析磁盘映像和文件系统。它是 Autopsy 数字取证平台的核心组件。

## 功能特性

- **文件系统分析**：支持多种文件系统（NTFS, FAT, EXT, HFS+ 等）
- **磁盘映像分析**：分析 raw, E01, AFF 等格式磁盘映像
- **数据恢复**：从已删除文件和未分配空间恢复数据
- **时间线分析**：生成文件系统活动时间线

## 主要工具

| 工具 | 功能 |
|------|------|
| fls | 列出文件和目录 |
| mmls | 显示磁盘分区表 |
| icat | 提取文件内容 |
| blkcat | 显示数据块内容 |
| fsstat | 文件系统统计信息 |
| ils | 列出 inode 信息 |

## 编译版本

| 版本 | 状态 | 日期 | 下载 |
|------|------|------|------|
| 4.12.1 | published | 2026-05-25 | sleuthkit-4.12.1-aarch64-linux-gnu.tar.gz |

## 编译说明

- 构建系统：autotools
- 编译器：clang/clang++
- 无额外依赖
- 注意事项：需移除 -Werror 标志

## 官方资源

- 官网：https://www.sleuthkit.org/
- GitHub：https://github.com/sleuthkit/sleuthkit